# Title: CMPE273-Assignment1
# Description: client for Spartan Messenger chat using gRPC in python3
# By: Neil Shah

import time
import grpc
import sys
import threading
import yaml
from functools import wraps
import AESCypher

import messenger_pb2
import messenger_pb2_grpc

AESKey = "This is a AES256 password" #default
RATE_LIMIT = 5 #default
PORT = 50051 #default

def getConfigs():
    with open('config.yaml','r') as c:
        configFile = yaml.load(c)
    global PORT
    global RATE_LIMIT
    try:
        PORT = configFile["port"]
        RATE_LIMIT = configFile["max_call_per_30_seconds_per_user"]
    except:
        print("Unable to fetch configs. Using default config settings.")
        
def userCheck(userName):
    userFound = False
    with open('config.yaml','r') as c:
        configFile = yaml.load(c)
    for u in configFile["users"]:
        if(userName.lower()==u.lower()):
            userFound = True
            break
    return userFound

def setAESKey(group):
    with open('client.yaml','r') as c:
        configFile = yaml.load(c)
    global AESKey
    try:
        AESKey = configFile["aesKey"][group]
    except:
        print("Unable to fetch AESKey from client.yaml; Using default key.")
        
def run(userName):

    def listenForMsgs():
        while 1:
            incoming_msgs = stub.ChatResponseStream(messenger_pb2.SessionID(connectionID=sessionID))
            for msg in incoming_msgs:
                if(msg.name==userName): continue
                if(msg.id==sessionID): 
                    decryptedMsg = cipher.decrypt(msg.message)
                    print("[%s]:%s" % (msg.name, decryptedMsg))

    def sendMessages(sessionID, userName):
        while 1:
            newMsg = input("")
            if(newMsg==""): continue
            encryptedMsg = cipher.encrypt(newMsg)
            status = stub.SendMessage(messenger_pb2.ChatMessage(id=sessionID,name=userName,message=encryptedMsg, readFlag=False))
            if(status.statusCode=="1"): print("[Spartan]: Failed to send message")
            if(status.statusCode=="2"): print("[Spartan]: Message failed to deliver. Can only send " + str(RATE_LIMIT) + " msgs per 30 seconds.") 
            time.sleep(0.01)


    channel = grpc.insecure_channel('localhost:' + str(PORT))
    try:
        grpc.channel_ready_future(channel).result(timeout=10)
    except grpc.FutureTimeoutError:
        print("Connection timeout. Unable to connect to port " + str(PORT))
        exit()
    else:
        print("[Spartan] Connected to Spartan Server at port " + str(PORT))

    stub = messenger_pb2_grpc.ChatServerStub(channel)

    receiver = getGroup(userName)
    sessionID = stub.Login(messenger_pb2.LoginRequest(sender=userName, receiver=receiver)).connectionID
    print("[Spartan] You have joined a group chat with: " + getGroupUsers(userName))
    
    setAESKey(receiver)
    cipher = AESCypher.AESCipher(AESKey)
    chatHistory = stub.GetChatHistory(messenger_pb2.SessionID(connectionID=sessionID))
    for chats in chatHistory: 
        if(chats.name=="Spartan"): print("[%s] :%s" % (chats.name, chats.message))
        else:
            decryptedMsg = cipher.decrypt(chats.message)
            print("[%s]:%s" % (chats.name, decryptedMsg))

    threading.Thread(target=listenForMsgs, daemon=True).start()
    sendMessages(sessionID, userName)


def getGroup(userName):
    with open('config.yaml','r') as c:
        configFile = yaml.load(c)
    for group in configFile["groups"]:
        for user in configFile["groups"][group]:
            if(userName==user): return group

def getGroupUsers(userName):
    with open('config.yaml','r') as c:
        configFile = yaml.load(c)
    users = ""
    for group in configFile["groups"]:
        if(userName in configFile["groups"][group]): 
            for user in configFile["groups"][group]:
                users += user + " "
    return users

#implementation for 1-1 chat. 
def getUserName():
    while True:
        userName = input("Enter your username: ")
        if(userCheck(userName)): return userName.lower()
        else: print("Sorry, that username is not registered. Please enter a valid username.")

#implementation for 1-1 chat.
def getReceiver(userName):
    with open('config.yaml','r') as c:
        configFile = yaml.load(c)
    
    print("Enter 1 for 1-1 chat")
    print("Enter 2 for group chat")
    while True:
        choice = int(input())
        if(choice==1 or choice==2): break
        else:
            print("Invalid choice, please enter 1 or 2")

    if(choice==1):
        print("Registered Users: ")
        for u in configFile["users"]: 
            if(u!=userName): print(u, end=' ', flush=True)
        print("")
        while True:
            receiver = input("Enter the name of the person you want to chat with: ")
            if(receiver==userName): 
                print("Sorry, you cannot chat with yourself.")
                continue
            if(userCheck(receiver)): return receiver.lower()
            else: print("sorry that user is not registered. Please enter a valid name")
    else:
        for group in configFile["groups"]:
            for user in configFile["groups"][group]:
                if(userName==user): return group



if __name__ == '__main__':
    userName = ""
    try:
        if(sys.argv[1] != ''): userName = sys.argv[1]
    except:
        print("Error: Enter command line argument for username.")
        exit()
    if(userCheck(userName)==False): 
        print("Error: Username is not registered. Please enter a valid username") 
        exit()
        
    try:
        getConfigs()
        run(userName)
    except KeyboardInterrupt:
        exit()