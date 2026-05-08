import util

# Your program should send TTLs in the range [1, TRACEROUTE_MAX_TTL] inclusive.
# 你的程序应发送 TTL 位于 [1, TRACEROUTE_MAX_TTL] 闭区间内的探测包。
# Technically IPv4 supports TTLs up to 255, but in practice this is excessive.
# 从技术上说 IPv4 支持最高 255 的 TTL，但实际使用中过大。
# Most traceroute implementations cap at approximately 30.  The unit tests
# assume you don't change this number.
# 大多数 traceroute 实现将上限设为约 30。单元测试假设你不会修改该值。
TRACEROUTE_MAX_TTL = 30

# Cisco seems to have standardized on UDP ports [33434, 33464] for traceroute.
# Cisco 似乎将 UDP 端口 [33434, 33464] 作为 traceroute 的惯用范围。
# While not a formal standard, it appears that some routers on the internet
# will only respond with time exceeeded ICMP messages to UDP packets send to
# those ports.  Ultimately, you can choose whatever port you like, but that
# range seems to give more interesting results.
# 虽然这不是正式标准，但互联网上有些路由器似乎只会对发送到这些端口的
# UDP 包返回 ICMP time exceeded 消息。你最终可以选择任意端口，不过
# 这个范围通常能得到更有意思的结果。
TRACEROUTE_PORT_NUMBER = 33434  # Cisco traceroute port number. / Cisco traceroute 端口号。

# Sometimes packets on the internet get dropped.  PROBE_ATTEMPT_COUNT is the
# maximum number of times your traceroute function should attempt to probe a
# single router before giving up and moving on.
# 互联网上的数据包有时会丢失。PROBE_ATTEMPT_COUNT 表示 traceroute 函数
# 在放弃当前路由器并继续下一跳之前，最多应尝试探测该路由器的次数。
PROBE_ATTEMPT_COUNT = 3

class IPv4:
    # Each member below is a field from the IPv4 packet header.  They are
    # listed below in the order they appear in the packet.  All fields should
    # be stored in host byte order.
    # 下面的每个成员都是 IPv4 数据包头部中的一个字段。字段按其在数据包中
    # 出现的顺序列出。所有字段都应以主机字节序存储。
    #
    # You should only modify the __init__() method of this class.
    # 你只应修改这个类的 __init__() 方法。
    version: int
    header_len: int  # Note length in bytes, not the value in the packet. / 注意这里是字节数，不是包内原始值。
    tos: int         # Also called DSCP and ECN bits (i.e. on wikipedia). / 也称为 DSCP 和 ECN 位。
    length: int      # Total length of the packet. / 数据包总长度。
    id: int
    flags: int
    frag_offset: int
    ttl: int
    proto: int
    cksum: int
    src: str
    dst: str

    def __init__(self, buffer: bytes):
        self.version = buffer[0] >> 4
        self.header_len = (buffer[0] & 0xf) * 4
        self.tos = buffer[1]
        self.length = int.from_bytes(buffer[2:4], 'big')
        self.id = int.from_bytes(buffer[4:6], 'big')
        self.flags = buffer[6] >> 5
        self.frag_offset = int.from_bytes(buffer[6:8], 'big') & 0x1fff
        self.ttl = buffer[8]
        self.proto = buffer[9]
        self.cksum = int.from_bytes(buffer[10:12], 'big')
        self.src = util.inet_ntoa(buffer[12:16])
        self.dst = util.inet_ntoa(buffer[16:20])
        
    def __str__(self) -> str:
        return f"IPv{self.version} (tos 0x{self.tos:x}, ttl {self.ttl}, " + \
            f"id {self.id}, flags 0x{self.flags:x}, " + \
            f"ofsset {self.frag_offset}, " + \
            f"proto {self.proto}, header_len {self.header_len}, " + \
            f"len {self.length}, cksum 0x{self.cksum:x}) " + \
            f"{self.src} > {self.dst}"


class ICMP:
    # Each member below is a field from the ICMP header.  They are listed below
    # in the order they appear in the packet.  All fields should be stored in
    # host byte order.
    # 下面的每个成员都是 ICMP 头部中的一个字段。字段按其在数据包中出现的
    # 顺序列出。所有字段都应以主机字节序存储。
    #
    # You should only modify the __init__() f unction of this class.
    # 你只应修改这个类的 __init__() 函数。
    type: int
    code: int
    cksum: int

    def __init__(self, buffer: bytes):
        self.type = buffer[0]
        self.code = buffer[1]
        self.cksum = int.from_bytes(buffer[2:4], 'big')

    def __str__(self) -> str:
        return f"ICMP (type {self.type}, code {self.code}, " + \
            f"cksum 0x{self.cksum:x})"


class UDP:
    # Each member below is a field from the UDP header.  They are listed below
    # in the order they appear in the packet.  All fields should be stored in
    # host byte order.
    # 下面的每个成员都是 UDP 头部中的一个字段。字段按其在数据包中出现的
    # 顺序列出。所有字段都应以主机字节序存储。
    #
    # You should only modify the __init__() function of this class.
    # 你只应修改这个类的 __init__() 函数。
    src_port: int
    dst_port: int
    len: int
    cksum: int

    def __init__(self, buffer: bytes):
        self.src_port = int.from_bytes(buffer[0:2], 'big')
        self.dst_port = int.from_bytes(buffer[2:4], 'big')
        self.len = int.from_bytes(buffer[4:6], 'big')
        self.cksum = int.from_bytes(buffer[6:8], 'big')

    def __str__(self) -> str:
        return f"UDP (src_port {self.src_port}, dst_port {self.dst_port}, " + \
            f"len {self.len}, cksum 0x{self.cksum:x})"

# TODO feel free to add helper functions if you'd like.
# TODO 如果愿意，可以在这里添加辅助函数。

def traceroute(sendsock: util.Socket, recvsock: util.Socket, ip: str) \
        -> list[list[str]]:
    """ Run traceroute and returns the discovered path.
    运行 traceroute，并返回发现的路径。

    Calls util.print_result() on the result of each TTL's probes to show
    progress.
    对每个 TTL 的探测结果调用 util.print_result()，用于展示进度。

    Arguments:
    sendsock -- This is a UDP socket you will use to send traceroute probes.
    recvsock -- This is the socket on which you will receive ICMP responses.
    ip -- This is the IP address of the end host you will be tracerouting.
    参数：
    sendsock -- 用于发送 traceroute 探测包的 UDP socket。
    recvsock -- 用于接收 ICMP 响应的 socket。
    ip -- 需要进行 traceroute 的终端主机 IP 地址。

    Returns:
    A list of lists representing the routers discovered for each ttl that was
    probed.  The ith list contains all of the routers found with TTL probe of
    i+1.   The routers discovered in the ith list can be in any order.  If no
    routers were found, the ith list can be empty.  If `ip` is discovered, it
    should be included as the final element in the list.
    返回：
    一个列表的列表，表示每个被探测 TTL 发现的路由器。第 i 个列表包含
    TTL 为 i+1 时发现的所有路由器。该列表中的路由器顺序可以任意。
    如果没有发现路由器，第 i 个列表可以为空。如果发现了 `ip`，它应作为
    返回列表的最后一个元素被包含进去。
    """
    discovered_routers = []
    for ttl in range(1, TRACEROUTE_MAX_TTL+1):
        sendsock.set_ttl(ttl)
        routers = []
        for _ in range(PROBE_ATTEMPT_COUNT):
            sendsock.sendto(b"traceroute probe", (ip, TRACEROUTE_PORT_NUMBER))
            if recvsock.recv_select():  
                buf, addr = recvsock.recvfrom()
                router_ip = addr[0]
                if router_ip not in routers:
                    routers.append(router_ip)
        util.print_result(routers, ttl)
        discovered_routers.append(routers)
        if ip in routers:
            break
    print(discovered_routers)
    return discovered_routers

if __name__ == '__main__':
    args = util.parse_args()
    ip_addr = util.gethostbyname(args.host)
    print(f"traceroute to {args.host} ({ip_addr})")
    traceroute(util.Socket.make_udp(), util.Socket.make_icmp(), ip_addr)
