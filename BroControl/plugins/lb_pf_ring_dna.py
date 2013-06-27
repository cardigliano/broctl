# This plugin runs pfdnacluster_master on each worker host before starting Bro
# when using PF_RING DNA load balancing.

import BroControl.plugin
import BroControl.config

class LBPFRingDNA(BroControl.plugin.Plugin):
    def __init__(self):
        super(LBPFRingDNA, self).__init__(apiversion=1)

    def name(self):
        return "lb_pf_ring_dna"

    def pluginVersion(self):
        return 1

    def cmd_start_pre(self, nodes):
        pfringid = int(BroControl.config.Config.pfringclusterid)
        if pfringid == 0:
            return nodes

        cmds = []
        workerhosts = set()

        # Build a list of (node, cmd) tuples.
        for nn in nodes:
            if nn.type != "worker" or nn.lb_method != "pf_ring_dna":
                continue

            # Make sure we have only one command per host (the choice of node
            # on each host is arbitrary), because a dna interface can be
            # opened by only one process.
            if nn.host not in workerhosts:
                workerhosts.add(nn.host)
                cmds += [(nn, "pfdnacluster_master -d -i %s -c %d -n %d" % (nn.interface, pfringid, int(nn.lb_procs)))]

            # Bro workers will use this pfdnacluster_master interface.
            nn.interface = "dnacluster:%d" % pfringid

        for (nn, success, out) in self.executeParallel(cmds):
            if not success:
                msg = "pfdnacluster_master failed on host %s" % nn.host
                if out:
                    msg += ": %s" % out[0]
                self.message(msg)

                # Since the command failed on this host, we won't attempt to
                # start any nodes on this host.
                nodes = [node for node in nodes if node.host != nn.host]

        return nodes

