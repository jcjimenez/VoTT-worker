#!/usr/bin/env python3

import os
import time

from azure.storage.queue.queueservice import QueueService
from azure.servicebus import ServiceBusService

class Task:
    '''
    Represents a queued training task.
    '''
    def __init__(self, id, pop_receipt, annotations_url, output_model_url, output_status_url):
        self.id = id
        self.pop_receipt = pop_receipt
        self.annotations_url = annotations_url
        self.output_model_url = output_model_url
        self.output_status_url = output_status_url
    def __str__(self):
        return str({id:self.id, pop_recepit:self.pop_receipt})

class TaskSource:
    '''
    Abstract class to allow switching between Storage Queues or Service Bus
    (or something else).
    '''
    @classmethod
    def is_supported(self):
        return False
    def receive(self):
        '''
        To be implemented by subclasses as a way to provide task(s) from either
        Storage Queues or Service Bus.
        '''
        raise Exception("Unimplemented")
    def commit(self, task):
        '''
        To be implemented by subclasses as a way to mark a given task as
        complete or deleted.
        '''
        raise Exception("Unimplemented")

class StorageQueueTaskSource(TaskSource):
    '''
    Azure Storage Queue implementation of TaskSource.
    '''
    def __init__(self):
        self.queue = QueueService(
            account_name=self.storage_account_name(),
            account_key=self.storage_key()
        )
        self.queue_name = os.environ.get('AZURE_STORAGE_QUEUE_NAME', 'training')
        self.queue_message_count = int(os.environ.get('AZURE_STORAGE_QUEUE_MESSAGE_COUNT', '1'))
    
    def __str__(self):
        return "Storage Queue (%s)" % self.storage_account_name()
    
    @classmethod
    def storage_account_name(self):
        return os.environ.get('AZURE_STORAGE_ACCOUNT_NAME')
    
    @classmethod
    def storage_key(self):
        return os.environ.get('AZURE_STORAGE_KEY')

    @classmethod
    def is_supported(self):
        return self.storage_account_name() and self.storage_key()

    def receive(self):
        messages = self.queue.get_messages(self.queue_name, self.queue_message_count)
        return [Task(message.id, message.pop_receipt, annotations_url='http://azure.com', output_model_url='http://azure.com', output_status_url='http://azure.com') for message in messages]

    def commit(self, task):
        self.queue.delete_message(self.queue_name, task.id, task.pop_receipt)

class ServiceBusTaskSource(TaskSource):
    '''
    Azure Service Bus implementation of TaskSource.
    '''
    def __init__(self):
        self.serviceBus = ServiceBusService(service_bus_namespace,
                                shared_access_key_name=os.environ.get('AZURE_SERVICE_BUS_ACCESS_KEY_NAME'),
                                shared_access_key_value=os.environ.get('AZURE_SERVICE_BUS_ACCESS_KEY_VALUE'))
    @classmethod
    def service_bus_namespace(self):
        return os.environ.get('AZURE_SERVICE_BUS_NAMESPACE')
    @classmethod
    def is_supported(self):
        return self.service_bus_namespace()

if __name__ == '__main__':
    if not (ServiceBusTaskSource.is_supported() or StorageQueueTaskSource.is_supported()):
        print("No supported task sources configured. Please set enviroment variables required for either ServiceBusTaskSource or StorageQueueTaskSource")
        exit(10)
    print("Accessing task queue...")
    source = ServiceBusTaskSource() if ServiceBusTaskSource.is_supported() else StorageQueueTaskSource()
    while True:
        print("Fetching tasks from %s..." % source)
        tasks = source.receive()
        if not tasks:
            print("No new tasks, sleeping.")
            time.sleep(10)
            continue
        for task in tasks:
            # TODO: Create sandbox temp space for task processing.
            # TODO: Download/initialize configured plugin.
            # TODO: Run training task.
            source.commit(task)
            