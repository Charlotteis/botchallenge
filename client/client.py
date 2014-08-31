from api import robotapi_pb2
from api import materials_pb2

from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.protocols.basic import Int32StringReceiver
from sys import stdout
import struct

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol

from greenlet import greenlet

import sys
import threading 
import logging
import random

logging.basicConfig(level=logging.DEBUG)

class RobotClientProtocol(Int32StringReceiver):

  def __init__(self, contextHandler):
    self.contextHandler = contextHandler
    self.timeout = None
    self.lastSentRequest = None
    self.connectionTimeout = None
  
  def stringReceived(self, msg):
    # We got a response, send it to the robot logic and await another command.
    if self.timeout:
      self.timeout.cancel()
      self.timeout = None
    response = robotapi_pb2.RobotResponse()
    response.ParseFromString(msg)
    logging.debug("Received response:\n<\n%s>", response)
    if self.lastSentRequest and self.lastSentRequest.key == response.key:
      self.contextHandler.handleResponse(response)
    else:
      logging.info("Recieved extra response for a retry. Response was for key: %s but I expected key %s", self.lastSentRequest.key, response.key)

  def handleTimeout(self):
    logging.info("TIMEOUT happened. I'm gonna retry that request.")
    self.sendRequest(self.lastSentRequest)

  def sendRequest(self, request):
    logging.debug("Sending request:\n<\n%s>", request)
    self.lastSentRequest = request
    self.sendString(request.SerializeToString())
    self.timeout = reactor.callLater(10, self.handleTimeout)

  def connectionMade(self):
    logging.info("Connected to server.")

  def connectionLost(self, reason):
    logging.info("Connection to server lost. Reason: " + str(reason))

class RobotClientProtocolFactory(ReconnectingClientFactory):

  def __init__(self, contextHandler):
    self.contextHandler = contextHandler
  
  def buildProtocol(self, addr):
    logging.info("Connected, creating client")
    return RobotClientProtocol(self.contextHandler)


class ContextHandler(object):

  def __init__(self, robot):
    self.serverEndpoint = TCP4ClientEndpoint(reactor, "192.168.0.22", 26656)
    self.robot = robot
    self.twisted_greenlet = None
    self.robot_greenlet = greenlet.getcurrent()
    self.twisted_greenlet = greenlet(self.startTwisted)
    self.twisted_greenlet.switch()

  def errback(error, extra):
    logging.error('Error setting up the protocol: %s (%s)', error, extra)

  def triggerFirstRequest(self, protocol):
    logging.info("Connected. Waiting for first robot request...")
    self.protocol = protocol
    # Switch to the robot execution context until it returns an request:
    request = self.robot_greenlet.switch(self.robot)
    # We've got our first command:
    self.protocol.sendRequest(request)

  def startTwisted(self):
    deferred = connectProtocol(self.serverEndpoint,
        RobotClientProtocol(self))
    deferred.addCallback(self.triggerFirstRequest)
    deferred.addErrback(self.errback)
    # Put reactor in a greenlet and switch to it immediately
    # When it's connected it'll start the robot greenlet
    reactor.run()
    logging.info("Reactor shut down.")

  def sendRequest(self, request):
    if self.twisted_greenlet.dead:
      sys.exit("Goodbye.")
    response = self.twisted_greenlet.switch(request)
    return response

  def handleResponse(self, response):
    # give the response to the robot context, and get the next request
    request = self.robot_greenlet.switch(response)
    if request:
      # We were given back a new request, let's send it.
      self.protocol.sendRequest(request)
    else:
      # There are no more commands, kill the reactor.
      logging.INFO("Received null request, ending.")
      reactor.stop()

class Robot(object):

  def __init__(self):
    self._contextHandler = ContextHandler(self)
    self.counter = random.randint(1, 2^16) 

  def _action(self, request):
    response = self._contextHandler.sendRequest(request)
    return response

  def _newAction(self):
    request = robotapi_pb2.RobotRequest()
    request.name = "katharosada"
    self.counter += 1
    request.key = self.counter
    return request

  def move(self, direction):
    request = self._newAction()
    request.action_request.move_direction = direction
    return self._action(request)

  def turn(self, direction):
    request = self._newAction()
    request.action_request.turn_direction = direction
    return self._action(request)

  def mine(self, direction):
    request = self._newAction()
    request.action_request.mine_direction = direction
    return self._action(request)

  def place(self, direction, material):
    request = self._newAction()
    request.action_request.place_direction = direction
    request.action_request.place_material.type = material
    return self._action(request)



class Dir:
  UP = robotapi_pb2.RobotActionRequest.UP
  DOWN = robotapi_pb2.RobotActionRequest.DOWN
  LEFT = robotapi_pb2.RobotActionRequest.LEFT
  RIGHT = robotapi_pb2.RobotActionRequest.RIGHT
  FORWARD = robotapi_pb2.RobotActionRequest.FORWARD
  BACKWARD = robotapi_pb2.RobotActionRequest.BACKWARD
  NORTH = robotapi_pb2.RobotActionRequest.NORTH
  SOUTH = robotapi_pb2.RobotActionRequest.SOUTH
  EAST = robotapi_pb2.RobotActionRequest.EAST
  WEST = robotapi_pb2.RobotActionRequest.WEST

