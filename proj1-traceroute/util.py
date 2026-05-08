import argparse
import select
import socket
import typing
import sys
import platform

# === Do Not Modify / 请勿修改 ===

# SELECT_TIMEOUT indicates how many seconds the select call will block in the
# event that no packets are received.  The smaller the number, the more likely
# our code is to give up and assume a router won't respond even when a packet
# is coming.  The larger the number, the slower our code will be when probing
# unresponsive routers.  In practice, 2 seconds acheives reasonable results.
# The tests don't depend on this number being anything in particular. It only
# impacts real runs.
# SELECT_TIMEOUT 表示在没有收到数据包时，select 调用最多阻塞多少秒。
# 该值越小，代码越可能过早放弃，并误以为某个路由器不会响应，即使响应包
# 其实正在到达途中。该值越大，在探测无响应路由器时程序越慢。实践中，
# 2 秒通常能取得合理效果。测试并不依赖这个具体数值，它只影响真实运行。
SELECT_TIMEOUT = 2

IPPROTO_ICMP = socket.IPPROTO_ICMP

IPPROTO_UDP = socket.IPPROTO_UDP


def ntohl(x):
    return socket.ntohl(x)


def htonl(x):
    return socket.htonl(x)


def htons(x):
    return socket.htons(x)


def ntohs(x):
    return socket.ntohs(x)


def inet_aton(x):
    return socket.inet_aton(x)


def inet_ntoa(x):
    return socket.inet_ntoa(x)


def inet_pton(x, y):
    return socket.inet_pton(x, y)


def inet_ntop(x, y):
    return socket.inet_ntop(x, y)


def gethostbyname(host: str):
    return socket.gethostbyname(host)


class Socket:
    __sock: socket.socket

    # Creates a UDP socket used for sending traceroute probes.  The starter
    # code calls this for you.
    # 创建一个用于发送 traceroute 探测包的 UDP socket。初始代码会替你调用它。
    @classmethod
    def make_udp(cls):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        return cls(sock)

    # Creates an ICMP socket used for receiving ICMP responses. The starter
    # code calls this for you.
    # 创建一个用于接收 ICMP 响应的 ICMP socket。初始代码会替你调用它。
    @classmethod
    def make_icmp(cls):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                 socket.IPPROTO_ICMP)
        except PermissionError:
            if platform.system() != "Darwin":
                print("PermissionError: please run as root.")
                sys.exit(1)

            # On MacOS, you can create a non-privileged ICMP socket.  The raw
            # socket is preferable as it's less fragile and cross platform, but
            # since that failed, may as well try it.
            # 在 MacOS 上，可以创建非特权 ICMP socket。raw socket 更理想，
            # 因为它更稳定且跨平台；但既然创建失败，这里就尝试备用方式。
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                                 socket.IPPROTO_ICMP)
        return cls(sock)

    def __init__(self, sock: socket.socket):
        self.__sock = sock

    # Only called on the UDP socket.  Changes the TTL on all future packets
    # sent on this socket to the provided value.
    # 只在 UDP socket 上调用。将该 socket 后续发送数据包的 TTL 改为给定值。
    def set_ttl(self, ttl: int):
        return self.__sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)

    # Only called on the UDP socket.  Sends a UDP packet to `address`.
    # `address` is a tuple containing a string representation of an IPv4
    # address, and the destination port.   The UDP packet payload is `b`.  The
    # UDP packet header is created by the `sendto` function based on the
    # provided information.
    # 只在 UDP socket 上调用。向 `address` 发送一个 UDP 包。
    # `address` 是一个元组，包含 IPv4 地址的字符串形式和目标端口。UDP 包
    # 的载荷是 `b`。UDP 头部会由 `sendto` 函数根据提供的信息自动创建。
    #
    # See: https://docs.python.org/3/library/socket.html#socket.socket.sendto
    # 参见：https://docs.python.org/3/library/socket.html#socket.socket.sendto
    def sendto(self, b: bytes, address: typing.Tuple[str, int]) -> int:
        return self.__sock.sendto(b, address)

    # Only called on the ICMP socket.  Recieves a packet from the socket.
    # Returns a `bytes` object containing the entirity of the packet
    # (including the IP headers).   Additionally returns the address of the
    # packet's sender.
    # 只在 ICMP socket 上调用。从 socket 接收一个数据包。返回一个 `bytes`
    # 对象，包含整个数据包，包括 IP 头部。同时还会返回发送该数据包的地址。
    #
    # See: https://docs.python.org/3/library/socket.html#socket.socket.recvfrom
    # 参见：https://docs.python.org/3/library/socket.html#socket.socket.recvfrom
    def recvfrom(self) -> typing.Tuple[bytes, typing.Tuple[str, int]]:
        return self.__sock.recvfrom(4096)

    # Only called on the ICMP socket.  Blocks until this socket has a packet
    # ready to be received by `recvfrom()`, or `SELECT_TIMEOUT` expires.
    # Returns true if packets are available for `recvfrom()`.
    # 只在 ICMP socket 上调用。阻塞等待该 socket 上有可供 `recvfrom()` 接收的
    # 数据包，或者直到 `SELECT_TIMEOUT` 超时。如果有可接收的数据包则返回 true。
    #
    # See: https://docs.python.org/3/library/select.html#select.select
    # 参见：https://docs.python.org/3/library/select.html#select.select
    def recv_select(self) -> bool:
        rlist, _, _ = select.select([self.__sock], [], [], SELECT_TIMEOUT)
        return rlist != []


def print_result(routers: list[str], ttl: int):
    if len(routers) == 0:
        print(f"{ttl: >2}: *")
        return

    for i, router in enumerate(routers):
        if i == 0:
            preamble = f"{ttl: >2}:"
        else:
            preamble = "   "

        try:
            hostname, _, _ = socket.gethostbyaddr(router)
            print(f"{preamble} {hostname} ({router})")
        except socket.herror:
            print(f"{preamble} {router}")


def parse_args():
    parser = argparse.ArgumentParser(prog='cs168 Traceroute')
    parser.add_argument('host')
    return parser.parse_args()
