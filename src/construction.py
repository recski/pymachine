import logging
from collections import defaultdict
from itertools import permutations

from fst import FSA
from machine import Machine
from monoid import Monoid
from control import PosControl
from constants import deep_cases

class Construction(object):
    def __init__(self, name, control):
        self.name = name

        if not isinstance(control, FSA):
            raise TypeError("control has to be an FSA instance")
        self.control = control

    def check(self, seq):
        logging.debug("""Checking {0} construction for matching with
                      {1} machines""".format(self.name, seq))
        for machine in seq:
            self.control.read_symbol(str(machine.control))

    def run(self, seq):
        # read the sequence first, and give it to the control
        self.check(seq)

        # if control got into acceptor state, do something
        if self.control.in_final():
            return self.act(seq)
        else:
            return None

    def last_check(self, seq):
        """last_check() is called after construction is activated by the
        spreading activation. Can be used for order checking for example"""
        return True

    def act(self, seq):
        """
        @return a sequence of machines, or @c None, if last_check() failed.
        """
        logging.debug("""Construction matched, running action""")
        # arbitrary python code, now every construction will have it
        # hardcoded into the code, later it will be done by Machine objects

class AppendConstruction(Construction):
    def __init__(self, name, control, act_from_left=True, append_to_left=True):
        Construction.__init__(self)
        # when check is done, and an action is needed,
        # order of actions on machines is left to right or reverse
        self.act_from_left = act_from_left

        # when check is done, and an action is needed,
        # and we already have two machines chosen by the self.act_from_left
        # order traverse, on which machine do we want to append the other one
        self.append_to_left = append_to_left

class VerbConstruction(Construction):
    """A default construction for verbs. It reads definitions, discovers
    cases, and builds a control from it. After that, the act() will do the
    linking process, eg. link the verb with other words, object, subject, etc.
    """
    def __init__(self, name, machine):
        self.name = name
        self.machine = machine
        self.case_locations = self.discover_cases()
        self.generate_control()

    def generate_control(self):
        cases = self.case_locations.keys()
        
        # this will be a hypercube
        control = FSA()

        # zero state is for verb
        control.add_state("0", is_init=True, is_final=False)

        # inside states for the cube, except the last, accepting state
        for i in xrange(1, pow(2, len(cases))):
            control.add_state(str(i), is_init=False, is_final=False)

        # last node of the hypercube
        control.add_state(int(pow(2, len(cases)),
                              is_init=False, is_final=True))

        # count every transition as an increase in number of state
        for path in permutations(cases):
            actual_state = 1
            for case in path:
                increase = pow(2, cases.index(case))
                new_state = actual_state + increase
                control.add_transition("CAS<{0}>".format(case),
                                       str(actual_state), str(new_state))
                actual_state = new_state

    def discover_cases(self, machine=None, d=None):
        if machine is None:
            machine = self.machine
        if d is None:
            d = defaultdict(list)

        for pi, p in enumerate(machine.base.partitions[1:]):
            pi += 1
            for part_machine in p:
                pn = part_machine.printname()
                if pn in deep_cases:
                    d[pn].append((machine, pi))
        return d

class TheConstruction(Construction):
    """NOUN<DET> -> The NOUN"""
    def __init__(self):
        control = FSA()
        control.add_state("0", is_init=True, is_final=False)
        control.add_state("1", is_init=False, is_final=False)
        control.add_state("2", is_init=False, is_final=True)
        control.add_transition("^the$", "0", "1")
        control.add_transition("^NOUN.*", "1", "2")

        Construction.__init__(self, "TheConstruction", control)

    def act(self, seq):
        logging.debug("""Construction matched, running last check""")
        self.last_check(seq)
        logging.debug("""TheConstruction matched, running action""")
        seq[1].control.pos += "<DET>"
        return [seq[1]]

class DummyNPConstruction(Construction):
    """NP construction. NP -> Adj* NOUN"""
    def __init__(self):
        control = FSA()
        control.add_state("0", is_init=True, is_final=False)
        control.add_state("1", is_init=False, is_final=True)
        control.add_transition("^ADJ.*", "0", "0")
        control.add_transition("^NOUN.*", "0", "1")

        Construction.__init__(self, "DummyNPConstruction", control)

    def act(self, seq):
        logging.debug("""Construction matched, running last check""")
        self.last_check(seq)
        logging.debug("""DummyNPConstruction matched, running action""")
        noun = seq[-1]
        adjs = seq[:-1]
        for adj in adjs:
            noun.append(adj)
        return [noun]

def test():
    a = Machine(Monoid("a"), PosControl("DET"))
    kek = Machine(Monoid("kek"), PosControl("ADJ"))
    kockat = Machine(Monoid("kockat"), PosControl("NOUN<CAS<ACC>>"))

    npc = DummyNPConstruction()
    thec = TheConstruction()

    res = npc.run([kek, kockat])
    res = thec.run([a] + res)
    print res[0]
    print res[0].control
    print res[0].base.partitions[1][0]


if __name__ == "__main__":
    test()

