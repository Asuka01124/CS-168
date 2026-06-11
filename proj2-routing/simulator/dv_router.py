"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####
        self.history = {}  # port -> {dst: last_advertised_latency}
        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        self.table[host] = TableEntry(
            dst=host,
            port=port,
            latency=self.ports.get_latency(port),
            expire_time=FOREVER,
        )
        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        
        ##### Begin Stage 2 #####
        entry = self.table.get(packet.dst)
        if entry is not None and entry.latency < INFINITY:
            self.send(packet, port=entry.port)
        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        # Determine which ports to advertise to
        if single_port is not None:
            ports = [single_port]
        else:
            ports = self.ports.get_all_ports()

        for port in ports:
            for dst, entry in self.table.items():
                # Determine what latency to advertise
                latency = entry.latency

                # Stage 8: Cap advertised latencies at INFINITY
                if latency > INFINITY:
                    latency = INFINITY

                # Stage 6: Split horizon
                if self.SPLIT_HORIZON and entry.port == port:
                    continue

                # Stage 7: Poison reverse
                if self.POISON_REVERSE and entry.port == port:
                    latency = INFINITY

                # Stage 10A: Incremental updates
                if not force:
                    last_advertised = self.history.get(port, {}).get(dst)
                    if last_advertised == latency:
                        continue

                # Send the advertisement
                self.send_route(port, dst, latency)

                # Update history
                if port not in self.history:
                    self.history[port] = {}
                self.history[port][dst] = latency
        ##### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####
        current_time = api.current_time()
        expired_dsts = []
        for dst, entry in self.table.items():
            if entry.expire_time <= current_time:
                if self.POISON_EXPIRED:
                    # Stage 9: Replace with poisoned entry
                    self.table[dst] = TableEntry(
                        dst=dst,
                        port=entry.port,
                        latency=INFINITY,
                        expire_time=current_time + self.ROUTE_TTL,
                    )
                else:
                    # Stage 5: Remove expired entries
                    expired_dsts.append(dst)

        for dst in expired_dsts:
            self.table.pop(dst)
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####
        link_latency = self.ports.get_latency(port)
        total_latency = route_latency + link_latency
        current_time = api.current_time()
        expire_time = current_time + self.ROUTE_TTL

        current_entry = self.table.get(route_dst)
        updated = False

        if current_entry is None:
            # New route: always accept
            self.table[route_dst] = TableEntry(
                dst=route_dst,
                port=port,
                latency=total_latency,
                expire_time=expire_time,
            )
            updated = True
        elif current_entry.port == port:
            # Rule 2: always accept from current next-hop
            self.table[route_dst] = TableEntry(
                dst=route_dst,
                port=port,
                latency=total_latency,
                expire_time=expire_time,
            )
            updated = True
        elif total_latency < current_entry.latency:
            # Strictly better route: accept
            self.table[route_dst] = TableEntry(
                dst=route_dst,
                port=port,
                latency=total_latency,
                expire_time=expire_time,
            )
            updated = True
        # else: not better, drop

        if updated:
            self.send_routes(force=False)
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####
        if self.SEND_ON_LINK_UP:
            self.send_routes(force=False, single_port=port)
        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####
        if self.POISON_ON_LINK_DOWN:
            # Replace all routes using this port with poison
            current_time = api.current_time()
            for dst, entry in list(self.table.items()):
                if entry.port == port:
                    self.table[dst] = TableEntry(
                        dst=dst,
                        port=port,
                        latency=INFINITY,
                        expire_time=current_time + self.ROUTE_TTL,
                    )
            self.send_routes(force=False)
        else:
            # Delete all routes using this port
            dsts_to_remove = [
                dst for dst, entry in self.table.items() if entry.port == port
            ]
            for dst in dsts_to_remove:
                self.table.pop(dst)
        ##### End Stage 10B #####

    # Feel free to add any helper methods!
