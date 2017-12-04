import pyqtgraph as pg
import numpy as np


BLUE = (0, 0, 100, 255)
RED = (100,0,0, 255)

brush=pg.mkBrush(color=(200, 10, 0,1))

brush = (30, 100, 2, 255)

TASK_BLOCKED   = 'Running'    
TASK_SUSPENDED = 'Suspended' 
TASK_RUNNING   = 'Ready'
TASK_READY     = 'Blocked'   

NODE_RADIUS = 2

class GraphNodes(pg.GraphItem):
    def __init__(self, x_offset, y_offset):
        self.x_offset = x_offset
        self.y_offset = y_offset
        
        self.dragPoint = None
        self.dragOffset = None
        self.textItems = []
        pg.GraphItem.__init__(self)
        
        self.scatter.setData(pxMode=False)

                
    def setCurrentState(self, state):
        self.nodes = {}
        self.nodes['Running'] =   {'x': 10,'y': 0,  'color': BLUE} 
        self.nodes['Suspended'] = {'x': 0, 'y': 0,  'color': BLUE} 
        self.nodes['Ready'] =     {'x': 0, 'y': -10,'color': BLUE}
        self.nodes['Blocked'] =   {'x': 0, 'y': 10, 'color': BLUE}

        self.nodes[state]['color'] = RED
        for key in self.nodes:
            node = self.nodes[key]

        self.scatter.clear()
        self.scatter.addPoints([
            {
                'pos': (self.nodes[key]['x'] + self.x_offset, self.nodes[key]['y'] + self.y_offset),
                'size': NODE_RADIUS * 2,
                'brush': self.nodes[key]['color'],
                'symbol': 'o',
            } for key in self.nodes 
        ])

    def setData(self, **kwds):
        self.data = kwds
        if 'pos' in self.data:
            npts = self.data['pos'].shape[0]
            self.data['data'] = np.empty(npts, dtype=[('index', int)])
            self.data['data']['index'] = np.arange(npts)
        self.updateGraph()
        
    def setTexts(self, text):
        for i in self.textItems:
            i.scene().removeItem(i)
        self.textItems = []
        for t in text:
            item = pg.TextItem(t)
            self.textItems.append(item)
            item.setParentItem(self)
        
    def updateGraph(self):
        pg.GraphItem.setData(self, **self.data)
        for i,item in enumerate(self.textItems):
            item.setPos(*self.data['pos'][i])

class GraphArrows():
    def __init__(self, x0, x1, y0, y1):
        self.arrowItemList = []
        self.arrowItemList.append(self.makeArrow(x0, x1, y0, y1))
        
    def makeArrow(self, x0, x1, y0, y1):
        if x0 == x1:
            angle = - 90*np.sign(y1-y0)
        else:
            angle = np.degrees(np.arctan((y1-y0)/(x1-x0))) 
        if np.sign(x1-x0) == 1:
            angle = angle + 180
            
        length = np.sqrt(np.power(y1-y0, 2) + np.power(x1-x0, 2)) - NODE_RADIUS * 2
        arrowTarget = (x1+np.cos(angle)*NODE_RADIUS,y1+np.sin(angle)*NODE_RADIUS)
             
        arrow = pg.ArrowItem(
            angle=angle,
            tipAngle=30,
            baseAngle=0,
            headLen=1,
            tailLen=length-1,
            tailWidth=0.3,
            pen=None,
            brush='w',
            pos=arrowTarget,
            pxMode = False
        )
        # text = pg.TextItem(
        #     text = "some sort of event",
        #     border='w',
        #     fill=(0, 0, 255, 100),
        #     angle=angle+180,
        #     anchor=(-0.1,1.2)
        # )
        # return [text,arrow]
        return [arrow]
            
class TaskGraphWidget(pg.GraphicsView):
    def __init__(self, stateHandler):
        self.viewBox = pg.ViewBox()
        
        self.viewBox.setAspectLocked(1.0)
        self.viewBox.setMouseEnabled(False, False)
        
        pg.GraphicsView.__init__(self)
        self.addItem(self.viewBox)
        self.setCentralWidget(self.viewBox)
       
        self.stateHandler = stateHandler
        self.stateHandler.subscribeToCurrentState(self.onStateChange)


    def makeLabel(self, text, x, y):
        t = pg.TextItem(
            text,
            anchor=(0.5,0.5),
            )
        t.setPos(x, y)
        return t

    def onStateChange(self, state):
        self.viewBox.clear()

        gridwidth = np.around(np.sqrt(len(state.tasks)))
        i = 0
        
        for task in state.tasks:            
              y = (i % gridwidth ) * -35
              x = (i // gridwidth) *  30
              i = i + 1 
              nodes = GraphNodes(x,y)
              nodes.setCurrentState(task.currentState)
              title = pg.TextItem(
                  text = "Task:"+task.taskName +"\n" +
                         "Event:" + task.eventName +"\n" +
                         "Priority:" + "TODO",
                  border='w',
                  fill=(0, 0, 0, 100),
                  anchor=(0,0.5),
                  angle = 0
                  )
              title.setPos(x+3, y+10)

              self.viewBox.addItem(nodes)            
              
              labels = [
                   self.makeLabel("Running",   x+10, y), 
                   self.makeLabel("Suspended", x,    y), 
                   self.makeLabel("Ready",     x,    y-10), 
                   self.makeLabel("Blocked",   x,    y+10) 
              ]

              for label in labels:
                  self.viewBox.addItem(label)
              self.viewBox.addItem(title)

            
              
              source = nodes.nodes[task.previousState]
              target = nodes.nodes[task.currentState]

              if task.enableArrow:
                  arrows = GraphArrows(
                      source['x'] + x,
                      target['x'] + x,
                      source['y'] + y,
                      target['y'] + y
                      )
                  for bunch in arrows.arrowItemList:
                      for item in bunch:
                          self.viewBox.addItem(item)
