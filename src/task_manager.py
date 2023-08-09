'''
This module is the abstraction layer for tasks.
'''

import threading
import queue

from src.indexing import IndexingTask

class TaskManager():
    '''
    TaskManager is the class that handles task submission and
    task consumption.
    '''
    def __init__(self, capacity: int):
        self.message_queue = queue.Queue(maxsize=capacity)

    def submit(self, task: IndexingTask):
        '''
        Submits a task to message queue.
        '''
        self.message_queue.put(task)

    def consume(self):
        '''
        Consumer loop that handles tasks.
        Because we always need to use config.toml as config file
        so as to run tabby scheduler command,
        we handle tasks synchronically in single threaded manner.
        '''
        while True:
            task: IndexingTask | None = self.message_queue.get()
            # Notification that the consumer loop is completed
            if task is None:
                break
            task.run()
            self.message_queue.task_done()

    def start_consumer(self):
        '''
        Starts the consumer loop in a thread.
        '''
        consumer = threading.Thread(target=self.consume)
        consumer.start()
