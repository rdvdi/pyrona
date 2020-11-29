"""
This file contains classes both for the meetings generation process and for 
the infection calculation one. The classes Team, Box and SpatialAgent are
needed only at the meetings table genertion phase. The classes InfectionAgent,
Infection are needed only during the subsequent infection probability 
clculation from the agent meetings table. 
"""
import numpy as np

# teams of conscripts along with a team of civilians with duty = None
class Team:
    def __init__(self, name, agent_idxs, duty, box):
        """
        - agent_idxs is a list with indexes (ids) of agents that belong to 
          this group.   
        - duty (period) is a dict with fields
          - on    i.e.  service period
          - off   i.e. holidays period
          - offset for rotations of multiple groups, e.g. to make one group
                    on  holiday while other in service
        - homeBox is an instance of class Box, contains homeBox dimensions - 
          e.g. the dimensions of "barracks" area. 
        """
        self.name = name
        self.agent_idxs = agent_idxs
        self.duty = duty
        self.homeBox = box
        self.currBox = None
        
# boxes to spawn agents in
class Box():
    def __init__(self, name, width, height, topLeftPoint):
        """
        Constructor accepts width and height of the box (in meters), as well
        as the starting "anchor" point of box the top left corner. The box
        then saves its absolute left, right, top and bottom coordinates for 
        (1) plotting box on canvas and (2) bouncing agents from its borders. 
        """
        self.name = name
        
        self.left   = eval(str(topLeftPoint["x"]))
        self.top    = eval(str(topLeftPoint["y"]))
        self.right  = eval(str(topLeftPoint["x"])) + width
        self.bottom = eval(str(topLeftPoint["y"])) - height

# spatial agent is used during meetings table generation phase
class SpatialAgent():
    def __init__(self, idx, allowed_box, dx, dy, conscripted,
                 color=(1.0, 1.0, 1.0, 1.0)):
        
        self.idx = idx

        self.x = np.random.randint(allowed_box.left, allowed_box.right)
        self.y = np.random.randint(allowed_box.bottom, allowed_box.top)
        
        self.allowed_box = allowed_box
        
        self.dx = dx
        self.dy = dy
        
        self.conscripted = conscripted
        self.color = color # for spatial agent: indicates if near another agent
        
    def transfer(self, to_box):
        
        self.x = np.random.randint(to_box.left, to_box.right)
        self.y = np.random.randint(to_box.bottom, to_box.top)
        
        self.allowed_box = to_box

class InfectionAgent():
    
    def __init__(self, idx, conscripted, infection, meets_dropout):
        self.idx = idx
        self.conscripted = conscripted
        self.infection = infection # object (of class   Infection)
        
        # fraction of meetings excluded from infection transmission claculation
        self.meets_dropout = meets_dropout
        
        # collect some statistics on-the-fly
        self.infection_transmitted = 0.0
        self.meetings_n = 0

def init_infect(agents, config):
    
    for agent in agents:
        
        if agent.conscripted:
            inf_frac = config['initiallyInfected']['conscriptsFraction']
        else:
            inf_frac = config['initiallyInfected'][ 'civiliansFraction']
        
        inf_dur = agent.infection.inf_dur
        inc_dur = agent.infection.inc_dur
        
        # for each infected there should be proportional amount incubating
        inc_frac = inc_dur/inf_dur * inf_frac
        
        # people were infected sometime in the past when the simulation began
        inc_ts = np.random.uniform(-inc_dur, 0)
        inf_ts = np.random.uniform(-inf_dur, 0)
        
        # flush 'init' incubation and infection and probability parts
        agent.infection.parts_inc[inc_ts] = inc_frac
        agent.infection.parts_inf[inf_ts] = inf_frac

class Infection():
    
    def __init__(self, inc_dur, inf_dur,
                 asympt_p, mask_p, quar_p,
                 incub_trx, sympt_trx, asympt_trx,
                 mask_eff_tx, mask_eff_rx, quar_eff):
        
        # incubation and infection period durations, seconds
        self.inc_dur = inc_dur * 24*60*60   
        self.inf_dur = inf_dur * 24*60*60   
        
        # small bits of infection yielded from meetings with another agents
        # incubation bits transition to infection when the time comes
        self.parts_inc = dict() #
        self.parts_inf = dict() #
        self.parts_imm = dict() #   key:timestamp, val: p (probability)
        
        # infection transfer probabilities for incubating and acute stages
        self.incub_trx  =  incub_trx
        self.sympt_trx  =  sympt_trx
        self.asympt_trx = asympt_trx
        
        # probabilities of being:
        self.asympt_p = asympt_p # asymptomatic
        self.mask_p = mask_p     # wearing mask
        self.quar_p = quar_p     # quarrantined (applies only if agent is
                                 # concripted _and_ symptomatically infected)
        
        # infection transfer countermeasures effectiveness
        self.mask_eff_tx = mask_eff_tx # from   this infection to another
        self.mask_eff_rx = mask_eff_rx # from   another infection to this
        self.quar_eff = quar_eff
        
    def transfer(self, eval_time, met_agent): # call for each other
        
        met_inf = met_agent.infection
        
        # total probabilities for agent to be incunating or acute infected
        # are sums of 'infection bits' transferred to this agent over time
        inc_p = sum(self.parts_inc.values())
        inf_p = sum(self.parts_inf.values())
        
        # mask wearing modifiers. Chance that there is no mask at all, 
        # plus chance that mask passes infection. 
        mask_mod = (1 - self.mask_p) + self.mask_p * (1 - self.mask_eff_tx)
        quar_mod = (1 - self.quar_p) + self.quar_p * (1 - self.quar_eff)
        
        # probability of infection being symptomatic and not
        asympt_p =     self.asympt_p
        sympt__p = 1 - self.asympt_p
        
        # bare probabilities of having the infection in three forms:
        # incubating, asymptmatic and symptomatic
        p_from_inc    = inc_p
        p_from_asympt = inf_p * asympt_p
        p_from__sympt = inf_p * sympt__p

        # transition probability modifiers for each infection form applied
        p_from_inc    *= self.incub_trx  * mask_mod
        p_from_asympt *= self.asympt_trx * mask_mod
        p_from__sympt *= self.sympt_trx  * mask_mod * quar_mod
        
        # total "outgoing" or "dispatched" probability of infecting the 
        # other party
        p_disp = p_from_inc + p_from_asympt + p_from__sympt
        
        # the method modifies the infection bits of the other party
        # directy. Therefore, it needs to take into account the other party
        # infetion reception modifers. In particular, if it wears a mask 
        met_nomask_p  = (1 - met_inf.mask_p)
        met_mask_pass =      met_inf.mask_p * (1 - met_inf.mask_eff_rx)
        met_mask_mod  = met_nomask_p + met_mask_pass
        
        # transferred infection decreases p of other party being healthy
        met_inc_p = sum(met_inf.parts_inc.values())
        met_inf_p = sum(met_inf.parts_inf.values())
        met_imm_p = sum(met_inf.parts_imm.values())
        
        met_hlty_p = 1 - (met_inc_p + met_inf_p + met_imm_p)
        
        p_recv = p_disp * met_hlty_p * met_mask_mod
        
        #   add an appropriate incubation probability to the other agent
        met_inf.parts_inc[eval_time] = p_recv
        
        #   record statistics
        met_agent.infection_transmitted += p_recv
    
    
    def update(self, eval_time, agent, place, config):
        
        """
        Dynamic mask usage probability update   based on which area agent is in.
        """
        if agent.conscripted:
            
            if place in ['civilian','sotilaskoti']:
                
                self.mask_p = config['mask']['coverage']['civilian']
                
            else:
                self.mask_p = config['mask']['coverage']['military']
        
        """
        1) Transfer developed incubation parts to infection ones
        """
        inc_ts = self.parts_inc.keys() # incubation start timestamps
        
        inc_ts = list(inc_ts) # detach from dict (to rm items during iteration)
        
        for inc_t in inc_ts:
            
            inc_end = inc_t + self.inc_dur # incubation period end
            
            if eval_time > inc_end:
                
                dev_inf = self.parts_inc.pop(inc_t) # developed infection
                                                    # probability bit
                self.parts_inf[inc_end] = dev_inf
        """
        2) Delete outdated infection parts
        """
        inf_ts = self.parts_inf.keys()
        
        inf_ts = list(inf_ts)
        
        for inf_t in inf_ts:
            
            inf_end = inf_t + self.inf_dur
            
            if eval_time > inf_end:
                
                imm_inf = self.parts_inf.pop(inf_t) # immunity after recovery
                                                    # probability bit
                self.parts_imm[inf_end] = imm_inf
        

def generate_spatial_entities(config):
    
    teams, boxes, agents = [], {}, []
    
    idx = 0 # global agents ids counter
    
    # each team has a home box and some number of agents to spawn
    for team_name, team_conf in config["teams"].items():
        
        # generate boxes
        box = Box(team_name, **team_conf["homeBox"]) # box stores its name
        boxes[team_name] = box                 # and is stored by its name
                               
        
        # populate agents
        team_agent_ids = []
        
        # random agents velocity (normal distribution)
        mu    = config["movementSpeed"]["mu"]
        sigma = config["movementSpeed"]["sigma"] * mu
        
        # scale distance covered per simulation step 
        T = 24*60*60                     # seconds in day
        dt = config["minSimulationStep"] # seconds in sim step
        
        n_steps = T/dt # simulation steps per day
        
        for _ in range(team_conf["nAgents"]):
                  
            # velocity vector amplitude
            A = np.random.normal(mu, sigma)
            
            # scale according to the number of simulation steps
            A = A / n_steps
            
            # random angle (uniform distribution)
            phi = np.random.uniform(0, 2*np.pi)
            
            # polar -> Carthesian
            dx = A*np.cos(phi)
            dy = A*np.sin(phi)
            
            agent = SpatialAgent(idx, box, dx, dy,
                                 team_conf["conscripted"])
            agents.append(agent)
            
            team_agent_ids.append(idx); idx += 1
        
        if team_conf["conscripted"]:
            duty = {
                "on"  : config["daysOnDuty"],
                "off" : config["daysOffDuty"],
                "offset"  : team_conf["rotationOffset"]}
        else:   
            duty = None
        
        team = Team(team_name, team_agent_ids, duty, box)
        teams.append(team)
        
    # add common soldier's shop/cafeteria if allowed in the config 
    if  config["sotilaskoti"]["allow"]:
        boxes["sotilaskoti"] = Box("sotilaskoti",
                                   **config["sotilaskoti"]["box"])
    
    return teams, boxes, agents


def generate_infection_entities(config):
    
    agents = []
    
    idx = 0
    
    for team_conf in config["teams"].values():
        
        for _ in range(team_conf["nAgents"]):
            
            # make an infection
            
            inc_dur = np.random.uniform(
                config['infection']['incubating']['daysMin'],
                config['infection']['incubating']['daysMax']
                )
            
            inf_dur = np.random.uniform(
                config['infection']['acute']['daysMin'],
                config['infection']['acute']['daysMax']
                )
            
            asympt_p = config['infection']['asymptomatic']['chance']
            
            if team_conf['conscripted']:
                mask_p = config['mask']['coverage']['military']
                
                if config['militaryQuarantine']['use']:
                    quar_p = config['militaryQuarantine']['coverage']
            else:
                mask_p = config['mask']['coverage']['civilian']
                quar_p = 0.0
            
            incub_trx  = config['infection'][  'incubating']['contagious']
            sympt_trx  = config['infection'][       'acute']['contagious']
            asympt_trx = config['infection']['asymptomatic']['contagious']
            
            mask_eff_tx = config['mask']['effectiveness'][   'wearer']
            mask_eff_rx = config['mask']['effectiveness']['recipient']
            quar_eff    = config['militaryQuarantine']['effectiveness']
            
            infection = Infection(inc_dur, inf_dur,
                                  asympt_p, mask_p, quar_p,
                                  incub_trx, sympt_trx, asympt_trx,
                                  mask_eff_tx, mask_eff_rx, quar_eff)
            
            if team_conf['conscripted']:
                meets_dropout = config['meetingsAvoided']['military']
            else:
                meets_dropout = config['meetingsAvoided']['civilian']
                
            agent = InfectionAgent(idx, team_conf["conscripted"],
                                   infection, meets_dropout)
            agents.append(agent)
        
            idx += 1
    
    return agents





















