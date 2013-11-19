# This plugin is used for PF_RING+DNA+libzero load balancing.  It runs
# pfdnacluster_master on each worker host before starting Bro, and renames
# the network interfaces on worker nodes (e.g., pfdnacluster_master might use
# "dna0", but all other programs use something like "dnacluster:21").

import BroControl.plugin
import BroControl.config

class LBPFRingDNA(BroControl.plugin.Plugin):
    def __init__(self):
        super(LBPFRingDNA, self).__init__(apiversion=1)
        self.pfdna_cmds = []

    def name(self):
        return "lb_pf_ring_dna"

    def pluginVersion(self):
        return 1

    def init(self):
        pfringid = int(BroControl.config.Config.pfringclusterid)
        if pfringid == 0:
            return True

        workerhosts = set()

        # Build a list of (node, cmd) tuples for later use, and rename the
        # worker network interfaces.
        for nn in self.nodes():
            if nn.type != "worker" or nn.lb_method != "pf_ring_dna":
                continue

            # Make sure we have only one command per host (the choice of node
            # on each host is arbitrary), because a dna interface can be
            # opened by only one process.
            if nn.host not in workerhosts:
                workerhosts.add(nn.host)

                # Using "-n 4,1" (rather than just "-n 4") allows another
                # application (such as capstats) to run while all 4 workers are
                # running (we cannot use "-n 5" because that would split
                # the traffic 5 ways).
                self.pfdna_cmds += [(nn, "pfdnacluster_master -d -i %s -c %d -n %d,1" % (nn.interface, pfringid, int(nn.lb_procs)))]

            # All other applications (Bro, capstats, etc.) will use this
            # pfdnacluster_master interface.
            nn.interface = "dnacluster:%d" % pfringid

        return True

    def cmd_start_pre(self, nodes):
        pfringid = int(BroControl.config.Config.pfringclusterid)
        if pfringid == 0:
            return nodes

        # Run the pfdnacluster_master program on the original netif (such
        # as "dna0").
        for (nn, success, out) in self.executeParallel(self.pfdna_cmds):
            if not success:
                msg = "pfdnacluster_master failed on host %s" % nn.host
                if out:
                    msg += ": %s" % out[0]
                self.message(msg)

                # Since the command failed on this host, we won't attempt to
                # start any nodes on this host.
                nodes = [node for node in nodes if node.host != nn.host]

        return nodes

