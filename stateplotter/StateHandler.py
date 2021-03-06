import json
from pprint import pprint
import copy
import dependencyGraph as dg

global TASK_BLOCKED   
global TASK_SUSPENDED 
global TASK_RUNNING   
global TASK_READY     

TASK_BLOCKED   = 'Blocked'    
TASK_SUSPENDED = 'Suspended' 
TASK_RUNNING   = 'Running'    
TASK_READY     = 'Ready'
TASK_NONEXISTENT = 'Nonexistent'



class StateSnapshot():
    def __init__(self, tasks, semaphores, event, isDeadlocked):
        self.tasks = tasks
        self.semaphores = semaphores    
        self.event = event
        self.isDeadlocked = isDeadlocked

# TODO make this a dict
class TaskState():
    def __init__(self,
                 taskName,
                 currentState,
                 previousState,
                 eventName,
                 requestedSemaphores,
                 heldSemaphores,
                 priority,
                 enableArrow
    ):
        self.currentState = currentState
        self.previousState = previousState
        self.taskName = taskName
        self.eventName = eventName
        self.requestedSemaphores = requestedSemaphores
        self.heldSemaphores = heldSemaphores
        self.priority = priority
        self.enableArrow = enableArrow
        
class StateHandler():
    def __init__(self):
        self.currentStateCallbacks = []
        self.statesCallbacks = [] 

    def subscribeToCurrentState(self, callback):
        self.currentStateCallbacks.append(callback)

    def subscribeToStates(self, callback):
        self.statesCallbacks.append(callback)
        
    def emitCurrentStateChange(self, index):
        newState = self.states[index]
        for cb in self.currentStateCallbacks:
            cb(newState)

    def emitStatesChange(self, states):
        for cb in self.statesCallbacks:
            cb(states)
            
    def setStates(self, states):
        self.states = states
        self.emitStatesChange(states)

    def stateFromFile(self, filename):
        try:
            json_data = open(filename).read()
            
        except IOError:
            print("file not found: " + filename)
            return

        try:
            data = json.loads(json_data)
        except ValueError:
            print("parsing error when reading " + filename)
            return
            
        self.setStates(self.generateState(data))

    def generateState(self, logFile):
        log = logFile["log"]
        nextState = StateSnapshot([],[],"", True )
        states = []
        semphNames = {}
        logLength = len(log)
        print("read log file: " + str(logLength) +" objects")
        counter = 0
        
        for obj in log:
            counter = counter + 1
            if counter % 100 == 0:
                print(str(counter) + "/" + str(logLength))
            eventName = str(obj["event"]["tick"]) +":"+ str(obj["event"]["data"]) 
            
            if obj["type"] == "SEMAPHORE":
                if( obj["event"]["data"]) == "Mutex created":
                    semphNames[obj["handle"]] = "semph{"+str(obj["source"]["file"])+", "+str(obj["source"]["line"])+"}"
                    nextState.semaphores.append(semphNames[obj["handle"]])
                    eventName = eventName + ":"+str(semphNames[obj["handle"]])  
                    
                elif(obj["event"]["data"] == "Take"):
                    runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING][0]
                    runningTask.heldSemaphores.append(semphNames[obj["handle"]])

                    if semphNames[obj["handle"]] in runningTask.requestedSemaphores:
                        runningTask.requestedSemaphores.remove(semphNames[obj["handle"]])
                    eventName = eventName + ":" +runningTask.taskName+"->"+ str(semphNames[obj["handle"]])    
                    runningTask.eventName = eventName
                    
                elif(obj["event"]["data"] == "Blocked on Take"):
                    runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING][0]
                    if not semphNames[obj["handle"]] in runningTask.requestedSemaphores:
                        runningTask.requestedSemaphores.append(semphNames[obj["handle"]])
              
                    runningTask.previousState = runningTask.currentState
                    runningTask.currentState = TASK_BLOCKED
                    eventName = eventName + ":"+ runningTask.taskName+"->"+ str(semphNames[obj["handle"]])  
                    runningTask.eventName = eventName
                    
                elif(obj["event"]["data"] == "Semaphore give"):
                    runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING]

                    if runningTask:
                        eventName = eventName + ":"+runningTask[0].taskName+"->"+str(semphNames[obj["handle"]])  
                        runningTask[0].heldSemaphores.remove(semphNames[obj["handle"]])
                        runningTask[0].eventName = eventName
                    else:
                        eventName = eventName + ":"+str(semphNames[obj["handle"]])  
        
            elif obj["type"] == "TASK_USER":
                if obj["event"]["data"] == "Create":
                    eventName = eventName + ":"+obj['taskName']  
                    nextState.tasks.append(copy.deepcopy(TaskState(
                        taskName = obj["taskName"],
                        currentState = TASK_NONEXISTENT,
                        previousState= TASK_NONEXISTENT,
                        eventName = eventName,
                        requestedSemaphores = [],
                        heldSemaphores = [],
                        priority = obj["taskPriority"],
                        enableArrow = False
                    )))

            elif obj["type"] == "TASK_KERNEL":
                if(obj["event"]["data"] == "Moved to ready"):
                    for task in nextState.tasks:
                        if task.taskName == obj["taskName"]:
                            task.previousState = task.currentState
                            task.currentState = TASK_READY
                            eventName = eventName + ":"+obj['taskName']  
                            task.eventName = eventName

                if(obj["event"]["data"] == "Task switched in"):
                    eventName = eventName + ":"+obj['taskName'] 
                    for task in nextState.tasks:
                        if task.currentState == TASK_RUNNING:
                            task.previousState = task.currentState
                            task.currentState = TASK_READY                             
                            task.eventName = eventName

                        if task.taskName == obj["taskName"]:
                            task.previousState = task.currentState
                            task.eventName = eventName
                            task.currentState = TASK_RUNNING
                            
                        
            elif obj["type"] == "DELAY":
                runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING][0]
                runningTask.previousState = runningTask.currentState
                runningTask.currentState = TASK_BLOCKED
                eventName = eventName + ":"+str(obj['duration'])
                runningTask.eventName = eventName
                
            nextState.isDeadlocked, dGraph = dg.check_for_deadlock(nextState)
            # if nextState.isDeadlocked:
            #     dg.show_dependency_graph(dGraph)
            nextState.event = eventName            
            states.append(copy.copy(nextState))
            nextState = copy.deepcopy(states[-1])
            
        print("generated " + str(len(states)) + " states")
        return states


    
