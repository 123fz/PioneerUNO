import random
import threading
import socket
import time
from concurrent.futures import ThreadPoolExecutor # 线程/进程池
import json


# 全局
server_close = False                                # 服务器是否即将关闭
thread_pool = ThreadPoolExecutor(max_workers=100)   # 公共线程池

# 声明
class UNOgame:
    pass

class Card:
    id = 0                  # 每张卡有唯一id 0~107
    # 0~24红卡 25~49绿 50~74蓝 75~99黄 100~103万能 104~107万能+4  其中红卡:0~18：0~9卡，19/20禁，21/22+2，23/24转，以此类推 共108张卡

    # UNO
    color = "red"
    text = "0"
    change_color = "white"  # 万能牌指定变色，未变色为white

    def __init__(s, id:int):
        s.id = id
        s.adjust()
        pass

    def adjust(s):
        """根据id调整数字number颜色color"""
        # 确定颜色
        if 0 <= s.id <= 24:
            s.color = "red"
        if 25 <= s.id <= 49:
            s.color = "green"
        if 50 <= s.id <= 74:
            s.color = "blue"
        if 75 <= s.id <= 99:
            s.color = "yellow"
        if 100 <= s.id <= 107:      # black卡为万能牌
            s.color = "black"
        # 确定卡面
        if 0 <= s.id <= 99: 
            if 0 <= (s.id % 25) <= 18:
                s.text = str((s.id % 25 + 1) // 2)
            if 19 <= (s.id % 25) <= 20:
                s.text = "/"
            if 21 <= (s.id % 25) <= 22:
                s.text = "+2"
            if 23 <= (s.id % 25) <= 24:
                s.text = "↔"
        if 100 <= s.id <= 103:
            s.text = "◑"
        if 104 <= s.id <= 107:
            s.text = "+4"

class Player:
    add = ()                    # 地址端口信息
    status = "empty"            # 连接状态： connecting 在线 / disconnect 游玩中掉线 / empty 空
    mutex = threading.Lock()    # 玩家互斥锁
    player_socket = None        # 该玩家的socket
    recv_thread = None          # 接收线程

    name = "default"            # 昵称
    handcards = []              # 手牌
    showcard = None             # 面前的牌
    seat = 0                    # 座位号 从1开始 0为无座位
    game = None                 # 所在游戏
    identity = "player"         # 玩家身份 player 普通玩家 / administrator 管理员 / spectator 旁观者(暂不开放)

    def __init__(s, game:UNOgame, player_socket:socket.socket, player_add):
        s.game = game
        s.player_socket = player_socket
        s.add = player_add
        s.recv_thread = threading.Thread(target=s.recv_fun)

    def recv_fun(s):                # 接收线程
        """
        接收线程
        命令格式:json格式，utf-8编码
            {
                "type": "command",
                "cmd": "命令内容",
                ...附加数据
            }

        # 全部命令：
            开始游戏:     "cmd":"gamestart"
            出牌:         "cmd":"playcard", "cardid":卡牌id(int)   例如 {"cmd":"playcard", "cardid":48}
            抽牌:         "cmd":"draw"
            整理手牌:     "cmd":"sort handcards"
            下一玩家:     "cmd":"next player"
            重洗牌库:     "cmd":"shuffle library"
            改昵称:       "cmd":"change name", "name":"更改的名字"
        """
        while s.status == "connecting":
            try:
                recv_data = s.player_socket.recv(1024).decode("utf-8")      # 接收
                try:
                    if isinstance(recv_data, str):
                        recv_data = json.loads(recv_data)
                    if not recv_data.isspace() and isinstance(recv_data, dict):
                        # 根据接收的命令调用UNOgame方法
                        try:
                            if recv_data["type"] == "command":
                                if recv_data["cmd"] == "gamestart":             # 开始游戏
                                    s.game.start()
                                elif recv_data["cmd"] == "playcard":            # 出牌
                                    s.game.playcard(s, recv_data["cardid"])
                                elif recv_data["cmd"] == "draw":                # 抽卡
                                    s.game.drawcard(s)
                                elif recv_data["cmd"] == "sort handcards":      # 整理手牌
                                    s.game.sortHandcards(s)
                                elif recv_data["cmd"] == "next player":         # 下一玩家
                                    s.game.nextPlayer(s)
                                elif recv_data["cmd"] == "shuffle library":     # 重洗牌库，仅等待时可用
                                    s.game.shuffleLibrary()
                                elif recv_data["cmd"] == "change name":
                                    s.game.changename(s, recv_data["name"])
                        except:
                            pass
                except:
                    # 命令无法解析
                    print("未知命令")
                    pass
            except:
                print(s.add, "断开连接")
                if s.game.status == "playing":
                    s.status = "disconnect"
                else:
                    s.status = "empty"
                break


class UNOgame:
    players = []                    # 玩家列表
    current_seat = 1                # 当前第几号玩家的回合，玩家的座位号
    allcards = []                   # 全卡列表
    library = []                    # 牌库
    discards = []                   # 弃牌堆
    direction = 1                   # 轮转方向：1 (1→2→3...) / -1 (3→2→1...)
    mutex = threading.Lock()        # 对局信息互斥锁
    periodicallySendThread = None   # 每秒更新对局信息线程
    status = "waiting"              # 对局状态  waiting等待玩家加入 / playing正在进行中 / sleeping休眠 / ending即将删除

    def __init__(s):
        s.periodicallySendThread = threading.Thread(target=s.periodicallySend)
        s.periodicallySendThread.start()
        for id in range(108):
            s.allcards.append(Card(id))

    def __allGameinfo(s):           # 返回全部对局信息，以json格式，内部隐藏方法不锁定
        gameinfo = {
            "type": "allGameinfo",                  # 信息类型：allGameinfo 全部对局信息 / publicGameinfo 公开对局信息
            "players": [],                          # 玩家信息列表
            "current_seat": s.current_seat,         # 当前玩家座位号
            "library": [],                          # 牌库
            "discards": [],                         # 弃牌堆
            "status": s.status                      # 对局状态
            }

        # players 玩家
        for player in s.players:
            temp_player = {
                "ip": player.add[0],
                "port": player.add[1],
                "name": player.name,
                "handcards": [],
                "showcard": None,
                "identity": player.identity
            }

            # handcards 玩家手牌
            for card in player.handcards:
                temp_card = {
                    "id": card.id,
                    "change_color": card.change_color
                }
                temp_player["handcards"].append(temp_card)

            # showcard 展示牌
            if player.showcard != None:
                temp_player["showcard"] = {
                    "id": player.showcard.id,
                    "change_color": player.showcard.change_color
                }

            gameinfo["players"].append(temp_player)

        # library 牌库
        for card in s.library:
            temp_card = {
                "id": card.id,
                "change_color": card.change_color
            }
            gameinfo["library"].append(temp_card)

        # discards 弃牌堆
        for card in s.discards:
            temp_card = {
                "id": card.id,
                "change_color": card.change_color
            }
            gameinfo["discards"].append(temp_card)
        return gameinfo
    
    def start(s):                   # 游戏开始
        print("游戏开始")
        if s.status == "playing":
            return
        s.mutex.acquire()
        s.status = "playing"
        s.direction = 1
        s.current_seat = 1

        # 初始化牌库
        for player in s.players:    # 玩家手牌清空
            player.handcards.clear()
        s.discards.clear()          # 弃牌堆清空
        s.library = s.allcards      # 重置牌库
        random.shuffle(s.library)   # 洗牌库

        s.mutex.release()
        s.broadcastInfo()

    def end(s):                     # 游戏结束
        print("游戏结束")
        s.mutex.acquire()
        s.status = "waiting"
        for player in s.players:    # 清除掉线玩家
            if player.status != "connecting":
                player.status = "empty"
        s.mutex.release()
        s.broadcastInfo()

    def nextPlayer(s, player:Player):               # 下个回合
        """下个回合"""
        s.mutex.acquire()
        if player.seat != s.current_seat:
            s.mutex.release()
            return
        s.current_seat += s.direction
        if s.current_seat > len(s.players):
            s.current_seat = 1
        elif s.current_seat < 1:
            s.current_seat = len(s.players)
        s.mutex.release()
        s.broadcastInfo()

    def playcard(s, player:Player, card_id:int):    # 出牌
        """出牌(玩家, 卡牌id)"""
        print("出牌", card_id)
        s.mutex.acquire()
        for i in range(len(player.handcards)):
            if player.handcards[i].id == card_id:
                player.showcard = player.handcards[i]
                s.discards.append(player.handcards.pop(i))
        s.mutex.release()
        s.broadcastInfo()

    def drawcard(s, player:Player):                 # 抽卡
        """抽卡(玩家)"""
        print("抽卡")
        s.mutex.acquire()
        if len(s.library) == 0:             # 没牌了就洗牌
            s.library.extend(s.discards)    # 弃牌堆合入牌库
            s.discards.clear()              
            random.shuffle(s.library)       # 洗牌库
        if len(s.library):                  # 避免出现弃牌堆也没牌的情况
            s.library[-1].change_color = "white"    # 重置万能牌颜色
            player.handcards.append(s.library.pop())
        s.mutex.release()
        s.broadcastInfo()

    def sortHandcards(s, player:Player):            # 整理手牌
        print("整理手牌")
        s.mutex.acquire()
        player.handcards.sort(key=lambda card:card.id)
        s.mutex.release()
        s.broadcastInfo()

    def shuffleLibrary(s):                          # 等待时重洗牌库
        s.mutex.acquire()
        if s.status != "waiting":
            s.mutex.release()
            return False
        for player in s.players:    # 玩家手牌清空
            player.handcards.clear()
        s.discards.clear()          # 弃牌堆清空
        s.library = s.allcards      # 重置牌库
        random.shuffle(s.library)   # 洗牌库
        s.mutex.release()
        s.broadcastInfo()
        return True

    def changename(s, player:Player, name):
        s.mutex.acquire()
        player.name = str(name)
        s.mutex.release()
        s.broadcastInfo()
        pass


    def broadcastInfo(s):                           # 向全部玩家更新对局信息，并检测玩家网络情况
        """向全部玩家更新对局信息，并检测玩家网络情况"""
        print(" b ", end="")
        s.mutex.acquire()
        for player in s.players:
            try:
                player.socket.send(s.__allGameinfo().encode("utf-8"))
            except:
                if s.status == "playing":
                    player.status = "disconnect"
                elif s.status == "waiting":
                    player.status = "empty"
                    s.discards.extend(player.handcards) # 丢出所有手牌
                    player.handcards.clear()
        s.mutex.release()

    def periodicallySend(s):
        """每秒更新对局信息"""
        while s.status != "sleeping" and s.status != "ending":
            s.broadcastInfo()
            time.sleep(1)
        pass

    def joinPlayer(s, player) -> bool:  # 玩家的加入与重连
        """玩家的加入与重连"""
        s.mutex.acquire()
        for p in s.players:
            if s.status == "waiting":
                # 寻找并加入空位
                if p.status == "empty":
                    player.seat = p.seat
                    p = player
                    break

            if s.status == "playing":
                # 掉线玩家重连
                if p.add[0] == player.add[0]:
                    player.seat = p.seat
                    p = player
                    break

        # 如果没有空位，则新开一个座位
        if player.seat == 0 and s.status == "waiting":    
            player.seat = len(s.players) + 1
            s.players.append(player)


        if player.seat != 0:    # 如果玩家加入成功，则座位号不为0，便开始接收玩家数据
            player.recv_thread.start()
            print(player.add, "加入游戏", player.seat, "号位")
            s.mutex.release()
            s.broadcastInfo()
            return True
        else:
            s.mutex.release()
            return False



def main():
    global server_close
    # 创建tcp套接字
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 绑定本地端口
    listen_socket.bind( ("", 18349) )

    # 设为监听模式
    listen_socket.listen(128)

    # 游戏对局对象
    game1 = UNOgame()

    while not server_close:
        # 等待客户端连接 .accept() 返回元组：(新的套接字, (客户端ip, 端口))
        new_client_socket, client_add = listen_socket.accept()

        temp_player = Player(game1, new_client_socket, client_add)
        if game1.joinPlayer(temp_player):
            print("%s已加入" % (str(client_add)))
        else:
            print("%s加入失败" % (str(client_add)))


    listen_socket.close()

if __name__ == "__main__":
    main()