import tkinter as tk
from tkinter.simpledialog import askinteger, askfloat, askstring    # 弹窗输入框
import random
import socket
import threading
import time

class Card:
    id = 0                  # 0~24红卡 25~49绿 50~74蓝 75~99黄 100~103万能 104~107万能+4  其中红卡:0~18：0~9卡，19/20禁，21/22+2，23/24转  共108张卡
    color = "red"           # 卡色
    text = ""               # 卡面
    change_color = "white"  # 万能牌变色
    hand_cards = None       # 手牌列表
    library_cards = None    # 牌库列表
    button = None           # 对应tkinter按钮

    def play(s, handcards, library):
        """出牌事件"""
        s.button.pack_forget()              # 卡牌消失
        for i in range(len(handcards)):
            if s.id == handcards[i].id:
                library.append(handcards.pop(i))    # 转移到牌堆
                break

    def draw(s):
        """抽牌事件"""
        if 100 <= s.id <= 107:  # 如果抽万能牌，重置颜色
            s.change_color = "white"
            s.button.config(fg="white", activeforeground="white")
        s.button.pack(side=tk.LEFT)

    def __init__(s, id, frame, handcards, library):
        """id:卡牌唯一指定id  frame:卡牌按钮所置框架  handcards/library:手牌与牌库列表"""
        if not isinstance(id, int):
            raise Exception("卡牌id不为整数")
        
        s.id = id
        s.hand_cards = handcards
        s.library_cards = library
        s.button = tk.Button(frame, width=2, height=1 ,font=("Arial", 20), borderwidth=3, relief=tk.RIDGE, command=lambda :s.play(handcards, library))

        # 确定颜色
        if 0 <= id <= 24:
            s.color = "red"
            s.button.config(fg="white", bg="red", activebackground="#990000", activeforeground="white")
        if 25 <= id <= 49:
            s.color = "green"
            s.button.config(fg="black", bg="lime", activebackground="#009900", activeforeground="black")
        if 50 <= id <= 74:
            s.color = "blue"
            s.button.config(fg="white", bg="blue", activebackground="#000099", activeforeground="white")
        if 75 <= id <= 99:
            s.color = "yellow"
            s.button.config(fg="black", bg="yellow", activebackground="#CCCC00", activeforeground="black")
        if 100 <= id <= 107:
            s.color = "black"
            s.button.config(bg="black", activebackground="#333333")
            if s.change_color == "green":
                s.button.config(fg="lime", activeforeground="lime")
            else:
                s.button.config(fg=s.change_color, activeforeground=s.change_color)

        # 确定卡面
        if 0 <= id <= 99: 
            if 0 <= (id % 25) <= 18:
                s.text = str((id % 25 + 1) // 2)
            if 19 <= (id % 25) <= 20:
                s.text = "/"
            if 21 <= (id % 25) <= 22:
                s.text = "+2"
            if 23 <= (id % 25) <= 24:
                s.text = "↔"
        if 100 <= id <= 103:
            s.text = "◑"
        if 104 <= id <= 107:
            s.text = "+4"
        s.button.config(text=s.text)


class Player:
    add = ()                    # 地址端口信息
    status = "empty"            # 连接状态： connecting 在线 / disconnect 游玩中掉线 / empty 空

    name = "default"            # 昵称
    handcards = []              # 手牌
    showcard = None             # 面前的牌
    seat = 0                    # 座位号 从1开始 0为无座位
    game = None                 # 所在游戏
    identity = "player"         # 玩家身份 player 普通玩家 / administrator 管理员 / spectator 旁观者(暂不开放)


class UNOgame:      # 客户端的游戏对象，存游戏数据，接收解析服务端返回数据
    # 网络
    net_status = "offline"      # 网络状态 offline 离线 / online 在线
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_add = ("192.168.0.104", 18349)
    recv_thread = None          # 接收线程

    # UNO
    me = None                       # 本人玩家对象
    players = []                    # 玩家列表
    current_seat = 1                # 当前第几号玩家的回合，玩家的座位号
    allcards = []                   # 全卡列表
    library = []                    # 牌库
    discards = []                   # 弃牌堆
    direction = 1                   # 轮转方向：1 (1→2→3...) / -1 (3→2→1...)
    mutex = threading.Lock()        # 对局信息互斥锁

    # tkinter



    

    def __init__(s) -> None:
        s.recv_thread = threading.Thread(target=s.recv_fun)
        # 加载108张牌
        for i in range(108):
            s.allcards.append(Card())
        pass

    def recv_fun(s):
        pass

    def start(s) -> bool:
        try:
            s.client_socket.connect(s.server_add)
        except:
            return False
        s.recv_thread.start()
        return True

# 抽卡
def draw(library, handcards):
    """从牌库顶抽一张卡到手牌，返回抽的那张牌，无牌可抽返回false"""
    card = False
    if len(library) > 0:
        card = library.pop()
        card.draw()
        handcards.append(card)
    return card

# 整理手牌
def sortcards(cards):
    """根据id整理手牌，返回卡组"""
    cards.sort(key=lambda card:card.id)
    try:
        for card in cards:
            card.button.pack_forget()
        for card in cards:
            card.button.pack(side=tk.LEFT)
    except:
        pass
    return cards

def connectNetwork(button:tk.Button, netStatusLable:tk.Label):
    """连接网络按钮事件"""
    if button.cget("text") == "连接网络":
        try:
            # 连接网络


            button.config(text="断开连接")
            netStatusLable.config(text="联机")
        except:
            pass
    elif button.cget("text") == "断开连接":
        button.config(text="连接网络")
        try:
            # 断开连接


            netStatusLable.config(text="单机")
        except:
            pass

def change_name(namebutton:tk.Button):
    name = askstring(title=" ", prompt="修改昵称(<=14字)")
    if not isinstance(name, str):
        return
    if not name.isspace() and name != "":
        name = name[0:14]   # 昵称不超14字
        namebutton.config(text=name)


def main():
    all_cards = []      # 全卡顺序列表，id查表
    library_cards = []  # 牌库
    hand_cards = []     # 手牌

    root = tk.Tk()
    root.title("先锋UNO!")

    # 个人/房间信息框
    info_frame = tk.Frame(root)
    info_frame.grid(row=0, column=0)

    # 牌桌
    table_frame = tk.Frame(root, relief=tk.GROOVE, borderwidth=10)
    table_frame.grid(row=0, column=1, padx=2, pady=5, ipadx=2, ipady=2, sticky=tk.N+tk.S+tk.W)

    # 按钮框
    button_frame = tk.Frame(root)
    button_frame.grid(row=1, column=0, sticky=tk.E)

    # 手牌
    hand_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    hand_frame.grid(row=1, column=1)


    # 信息框内容
    tk.Label(info_frame, text="昵称").grid(row=0, column=0)

    namebutton = tk.Button(info_frame, bg="#f0f0f0", relief=tk.SOLID, borderwidth=1, text="player")
    namebutton.config(command=lambda:change_name(namebutton))
    namebutton.grid(row=0, column=1, sticky="ew")

    netStatusLable = tk.Label(info_frame, text="单机")
    netStatusLable.grid(row=1, column=0)
    connectNetworkButton = tk.Button(info_frame, text="连接网络", relief=tk.RIDGE, borderwidth=3)
    connectNetworkButton.config(command=lambda:connectNetwork(connectNetworkButton, netStatusLable))
    connectNetworkButton.grid(row=1, column=1, pady=2)

    tk.Label(info_frame, text="4人").grid(row=2, column=0)
    tk.Label(info_frame, text="房间成员").grid(row=2, column=1)
    # 成员框
    member_frame = tk.Frame(info_frame, relief=tk.SOLID, borderwidth=1)
    member_frame.grid(row=3, column=0, columnspan=2, padx=5, sticky="we")
    tk.Label(member_frame, text="Fz", anchor=tk.W).pack(fill=tk.X)
    tk.Label(member_frame, text="节操君", anchor=tk.W).pack(fill=tk.X)
    tk.Label(member_frame, text="尾巴长出来了唷~！", anchor=tk.W).pack(fill=tk.X)
    tk.Label(member_frame, text="快乐吃货", anchor=tk.W).pack(fill=tk.X)
    tk.Label(member_frame, text="012345678901234", anchor=tk.W).pack(fill=tk.X)

    # 牌桌布局
    cards_frame = tk.Frame(table_frame)             # 卡组信息框
    cards_frame.grid(row=0, column=0, columnspan=3, pady=5)
    leftpl_frame = tk.Frame(table_frame)            # 左侧玩家框
    leftpl_frame.grid(row=1, column=0)
    center_table_frame = tk.Frame(table_frame, bg="green")      # 中间牌桌框
    center_table_frame.grid(row=1, column=1, rowspan=6, ipadx=10, ipady=10, padx=5, pady=5)
    rightpl_frame = tk.Frame(table_frame)           # 右侧玩家框
    rightpl_frame.grid(row=1, column=2)

    tk.Label(cards_frame, text="牌库剩余: ").pack(side=tk.LEFT)
    tk.Label(cards_frame, text="65", relief=tk.SOLID, borderwidth=2, bg="black", fg="white").pack(side=tk.LEFT)

    pl1_frame = tk.Frame(leftpl_frame)
    pl1_frame.pack(fill=tk.X, pady=3)
    tk.Button(pl1_frame, width=2, height=1 ,font=("Arial", 20), borderwidth=3, relief=tk.RIDGE, text="+2", fg="white", bg="red", activebackground="#990000", activeforeground="white").pack(side=tk.RIGHT, padx=3)
    tk.Label(pl1_frame, text="6", width=2, bg="black", fg="white").pack(side=tk.RIGHT)
    tk.Label(pl1_frame, text="Fz").pack(side=tk.RIGHT)
    tk.Label(pl1_frame, text="(1)").pack(side=tk.LEFT)
    
    pl2_frame = tk.Frame(leftpl_frame)
    pl2_frame.pack(fill=tk.X, pady=3)
    tk.Button(pl2_frame, width=2, height=1 ,font=("Arial", 20), borderwidth=3, relief=tk.RIDGE, text="+4", fg="blue", bg="black", activebackground="#333333", activeforeground="blue").pack(side=tk.RIGHT, padx=3)
    tk.Label(pl2_frame, text="1", width=2, bg="black", fg="white").pack(side=tk.RIGHT)
    tk.Label(pl2_frame, text="尾巴长出来了哟~").pack(side=tk.RIGHT)
    tk.Label(pl2_frame, text="(2)").pack(side=tk.LEFT)

    pl4_frame = tk.Frame(rightpl_frame)
    pl4_frame.pack(fill=tk.X, pady=3)
    tk.Button(pl4_frame, width=2, height=1 ,font=("Arial", 20), borderwidth=3, relief=tk.RIDGE, text="5", fg="white", bg="red", activebackground="#990000", activeforeground="white").pack(side=tk.LEFT, padx=3)
    tk.Label(pl4_frame, text="5", width=2, bg="black", fg="white").pack(side=tk.LEFT)
    tk.Label(pl4_frame, text="节操君").pack(side=tk.LEFT)
    tk.Label(pl4_frame, text="(4)").pack(side=tk.RIGHT)

    pl3_frame = tk.Frame(rightpl_frame)
    pl3_frame.pack(fill=tk.X, pady=3)
    tk.Button(pl3_frame, width=2, height=1 ,font=("Arial", 20), borderwidth=3, relief=tk.RIDGE, text="2", fg="white", bg="blue", activebackground="#000099", activeforeground="white").pack(side=tk.LEFT, padx=3)
    tk.Label(pl3_frame, text="15", width=2, bg="black", fg="white").pack(side=tk.LEFT)
    tk.Label(pl3_frame, text="快乐吃货").pack(side=tk.LEFT)
    tk.Label(pl3_frame, text="(3)").pack(side=tk.RIGHT)


    tk.Label(center_table_frame, text="现在\n轮到", font=("Arial", 20), fg="#CCFFCC", bg="green").pack(pady=5)
    tk.Label(center_table_frame, text="(4)", font=("Arial", 20), fg="#CCFFCC", bg="green").pack()


    # 加载所有108张牌
    for i in range(108):
        card = Card(i, hand_frame, hand_cards, library_cards)
        all_cards.append(card)
        library_cards.append(card)
    
    # 洗牌库
    random.shuffle(library_cards)

    # 抽卡/整理 按钮
    tk.Label(button_frame, text="手牌").pack(fill=tk.X, side=tk.LEFT)
    tk.Button(button_frame, text="抽卡！", command=lambda:draw(library_cards, hand_cards)).pack(fill=tk.X)
    tk.Button(button_frame, text="整理", command=lambda:sortcards(hand_cards)).pack(fill=tk.X)

    root.mainloop()


if __name__ == "__main__":
    main()