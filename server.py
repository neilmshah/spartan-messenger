# Title: CMPE273-Assignment1
# Description: server for Spartan Messenger chat using gRPC in python3
# By: Neil Shah

from concurrent import futures
import time
import threading
import yaml
from uuid import uuid4
from functools import wraps

import grpc

import messenger_pb2
import messenger_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24
LRU_CACHE_SIZE = 5 #default
RATE_LIMIT = 5 #default
PORT = 50051 #default

def getConfigs():
    with open('config.yaml','r') as c:
        configFile = yaml.load(c)
    global LRU_CACHE_SIZE 
    global PORT
    global RATE_LIMIT
    try:
        LRU_CACHE_SIZE = configFile["max_num_messages_per_user"]
        PORT = configFile["port"]
        RATE_LIMIT = configFile["max_call_per_30_seconds_per_user"]
    except:
        print("Unable to fetch configs. Using default config settings.")



class SpartanMessenger(messenger_pb2_grpc.ChatServerServicer):
    def __init__(self):
        self.userConnections = []
        self.chatMessages = {}
        self.msgTimeStamps = []
    
    #decorator
    def lruCache(func):
        def function_wrapper(self, msg, rate):
            chatSession = self.chatMessages[msg.id]
            if(rate==False and len(chatSession)==LRU_CACHE_SIZE): chatSession.pop(0)
            return func(self, msg, rate)
        return function_wrapper
    
    #decorator
    def rateLimit(func):
        def function_wrapper(self, msg, rate_limit):
            rateLimit = False
            userFound = False
            startTime = time.time()
            for userMsg in self.msgTimeStamps:
                if(userMsg["user"]==msg.name):
                    userFound = True
                    elapsedTime = startTime - userMsg["timeStamp"]
                    if(elapsedTime>30): 
                        userMsg["timeStamp"] = startTime
                        userMsg["msgCount"] = 1
                    else:
                        if(userMsg["msgCount"]>=RATE_LIMIT): 
                            rateLimit = True
                            break
                        userMsg["msgCount"] += 1
            if(userFound==False):
                self.msgTimeStamps.append({'user':msg.name, 'timeStamp':startTime, 'msgCount':1})
            return func(self, msg, rateLimit)
        return function_wrapper


    @rateLimit
    @lruCache
    def appendChat(self, msg, rateLimitCrossed=False):
        if(rateLimitCrossed): return "2"
        chatSession = []
        if(msg.id in self.chatMessages): chatSession = self.chatMessages[msg.id]
        else: self.chatMessages[msg.id] = chatSession
        chatSession.append(msg)
        self.chatMessages[msg.id] = chatSession
        return "0"
    
    def Login(self, request, context):
        uniqueID = ""
        for conn in self.userConnections:
            if(conn['receiver']==request.receiver):
                uniqueID = conn['id']
                break
        if(uniqueID==""):
            uniqueID = str(uuid4())
            self.userConnections.append({'sender':request.sender,'receiver':request.receiver,'id':uniqueID})
            self.chatMessages[uniqueID] = []
        return messenger_pb2.LoginResponse(connectionID=uniqueID)

    def GetChatHistory(self, request, context):
        chatHistory = []
        if(request.connectionID in self.chatMessages): chatHistory = self.chatMessages[request.connectionID]
        if(len(chatHistory)==0):
            yield(messenger_pb2.ChatMessage(id=request.connectionID, name="Spartan", message="No messages saved in history.", readFlag=True))
        else:
            for msg in chatHistory:
                msg.readFlag = True
                yield msg
            self.chatMessages[request.connectionID]=chatHistory

    def ChatResponseStream(self, request, context):
        chatSession = []
        while True:
            if(request.connectionID in self.chatMessages): 
                chatSession = self.chatMessages[request.connectionID]
                for msg in chatSession:
                    if(msg.readFlag==False): 
                        yield msg
                        msg.readFlag = True

    def SendMessage(self, request, context):
        #print("[%s]:%s" % (request.name, request.message))
        try:
            requestStatus = self.appendChat(request, False)
        except ValueError:
            requestStatus = "1"
        return messenger_pb2.Status(statusCode=requestStatus)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    messenger_pb2_grpc.add_ChatServerServicer_to_server(SpartanMessenger(), server)
    getConfigs()
    print("Spartan server started on port " + str(PORT) + ".")
    server.add_insecure_port('[::]:'+str(PORT))
    server.start()
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
        #exit()


if __name__ == '__main__':
    serve()
