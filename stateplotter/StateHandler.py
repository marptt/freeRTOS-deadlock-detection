import json
from pprint import pprint
import copy

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
    def __init__(self, tasks, semaphores, event):
        self.tasks = tasks
        self.semaphores = semaphores
        self.event = event

# TODO make this a dict
class TaskState():
    def __init__(self,
                 taskName,
                 currentState,
                 previousState,
                 eventName,
                 requestedSemaphores,
                 heldSemaphores,
                 enableArrow
    ):
        self.currentState = currentState
        self.previousState = previousState
        self.taskName = taskName
        self.eventName = eventName
        self.requestedSemaphores = requestedSemaphores
        self.heldSemaphores = heldSemaphores
        self.enableArrow = enableArrow
        
class StateHandler():
    def __init__(self):
        self.currentStateCallbacks = []
        self.statesCallbacks = [] 

        self.logFile = ""
        json_data=open("logFile.json").read()

        data = json.loads(json_data)

        #pprint(data)
        
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

    def stateFromFile(self):
        json_data=open("logFile.json").read()
        data = json.loads(json_data)
        self.setStates(self.generateState(data))
        
    def generateState(self, logFile):
        log = logFile["log"]

        nextState = StateSnapshot( [],[],"" )
        states = []
        
        for obj in log:
            eventName = str(obj["event"]["data"])
            nextState.event = eventName
            
            if obj["type"] == "SEMAPHORE":
                if( obj["event"]["data"]) == "Mutex created":
                    nextState.semaphores.append(str(obj["handle"]))
                elif(obj["event"]["data"] == "Take"):
                    runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING][0]
                    runningTask.heldSemaphores.append(obj["handle"])

                elif(obj["event"]["data"] == "Blocked on Take"):
                    runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING][0]
                    runningTask.requestedSemaphores.append(obj["handle"])
                    runningTask.previousState = runningTask.currentState
                    runningTask.currentState = TASK_BLOCKED

                elif(obj["event"]["data"] == "Semaphore give"):
                    runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING]
                    if runningTask:
                        runningTask[0].heldSemaphores.remove(obj["handle"])
                    
            elif obj["type"] == "TASK_USER":
                if obj["event"]["data"] == "Create":
                    nextState.tasks.append(copy.deepcopy(TaskState(
                        taskName = obj["taskName"],
                        currentState = TASK_NONEXISTENT,
                        previousState= TASK_NONEXISTENT,
                        eventName = eventName,
                        requestedSemaphores = [],
                        heldSemaphores = [],
                        enableArrow = False
                    )))

            elif obj["type"] == "TASK_KERNEL":
                if(obj["event"]["data"] == "Moved to ready"):
                    for task in nextState.tasks:
                        if task.taskName == obj["taskName"]:
                            task.previousState = task.currentState
                            task.currentState = TASK_READY
                            
                if(obj["event"]["data"] == "Task switched in"):
                    for task in nextState.tasks:
                        if task.currentState == TASK_RUNNING:
                            task.previousState = task.currentState
                            task.currentState = TASK_READY

                        if task.taskName == obj["taskName"]:
                            task.previousState = task.currentState
                            task.currentState = TASK_RUNNING
                            
                        
            elif obj["type"] == "DELAY":
                
                runningTask = [task for task in nextState.tasks if task.currentState == TASK_RUNNING][0]
                runningTask.previousState = runningTask.currentState
                runningTask.currentState = TASK_BLOCKED

                
            states.append(copy.copy(nextState))
            nextState = copy.deepcopy(states[-1])

        return states

    def mutexCreated():
        print("sdfh")
    
    def testStates(self):
        self.setStates( [
            StateSnapshot(
                [
                    TaskState(
                        taskName="egg",
                        currentState=TASK_SUSPENDED,
                        previousState=TASK_READY,
                        eventName="something caused this",
                        requestedSemaphores = [ "GreenSemaphore"],
                        heldSemaphores = [ "BlueSemaphore"],
                        enableArrow = True
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_SUSPENDED,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = [],
                        enableArrow = True
                    )],
                ["RedSemaphore", "GreenSemaphore", "BlueSemaphore"],
                'something happened first'
            ),
            StateSnapshot(
                [
                    TaskState(
                        taskName="egg",
                        currentState=TASK_BLOCKED,
                        previousState=TASK_SUSPENDED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = [ "RedSemaphore"],
                        enableArrow = False
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = [  "RedSemaphore"],
                        enableArrow = True
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = ["RedSemaphore"],
                        enableArrow = False
                    )
                ],
                ["RedSemaphore", "GreenSemaphore", "BlueSemaphore"],
                'something happened then'
            ),
            StateSnapshot(
                [
                    TaskState(
                        taskName="egg",
                        currentState=TASK_SUSPENDED,
                        previousState=TASK_READY,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = ["RedSemaphore"],
                        enableArrow = False
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = ["RedSemaphore"],
                        enableArrow = True
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = ["RedSemaphore"],
                        heldSemaphores = [],
                        enableArrow = False
                    ),
                    TaskState(
                        taskName="egg",
                        currentState=TASK_SUSPENDED,
                        previousState=TASK_READY,
                        eventName="something caused this",
                        requestedSemaphores = ["RedSemaphore"],
                        heldSemaphores = [],
                        enableArrow = False
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = ["BlueSemaphore"],
                        enableArrow = True
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = [],
                        enableArrow = False
                    ),
                    TaskState(
                        taskName="egg",
                        currentState=TASK_SUSPENDED,
                        previousState=TASK_READY,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = [],
                        enableArrow = False
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = [],
                        enableArrow = True
                    ),
                    TaskState(
                        taskName="bacon",
                        currentState=TASK_READY,
                        previousState=TASK_BLOCKED,
                        eventName="something caused this",
                        requestedSemaphores = [],
                        heldSemaphores = [],
                        enableArrow = False
                    )                    
                ],
                ["RedSemaphore", "GreenSemaphore", "BlueSemaphore"],
                'something happened then'
            )
        ])


    
