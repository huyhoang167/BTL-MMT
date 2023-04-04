from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"
SESSION_FILE = "session.txt"

class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    SWITCHING = 3
    state = INIT
    
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3    
    DESCRIBE = 4
    SWITCH = 5
    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
                
        self.bytesReceived = 0
        self.startTime = 0
        self.lossCounter = 0
        self.list_movie = [' ',' ',' ',' ',' ',' ']
        # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
    def createWidgets(self):
        """Build GUI."""
        # Create Setup buttonpy
        self.setup = Button(self.master, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'),relief="raised")
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=2, column=0, padx=2, pady=2)
        self.setup["state"] = "normal"
        
        # Create Play button		
        self.start = Button(self.master, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=2, column=1, padx=2, pady=2)
        self.start["state"] = "disabled"
        
        # Create Pause button			
        self.pause = Button(self.master, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=2, column=2, padx=2, pady=2)
        self.pause["state"] = "disabled"
        
        # Create Teardown button
        self.teardown = Button(self.master, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=2, column=3, padx=2, pady=2)
        self.teardown["state"] = "disabled"
        
        #Create describe button
        self.describe = Button(self.master, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.describe["text"] = "Describe"
        self.describe["command"] =  self.describeSession
        self.describe.grid(row=2, column=4, padx=2, pady=2)
        self.describe["state"] = "disabled"

        #Create describe button
        self.switch = Button(self.master, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.switch["text"] = "Switch"
        self.switch["command"] =  self.Switch
        self.switch.grid(row=1, column=4, padx=2, pady=2)
        self.switch["state"] = "disabled"
        # Create a label to display the movie
        self.label = Label(self.master, height=20, bg = "black")
        self.label.grid(row=0, column=0, columnspan=6, sticky=W+E+N+S, padx=5, pady=5) 
                
        # Create a label to display the time
        self.timeBox = Label(self.master, width=12, text="00:00", bg = "#52796f", fg= "white",font=("Times", 11, 'bold') )
        self.timeBox.grid(row=1, column=1, columnspan=3, sticky=W+E+N+S, padx=5, pady=5)

    def setupMovie(self):
        """Setup button handler."""
        self.sendRtspRequest(self.SETUP)
    
    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy() # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
        if self.frameNbr != 0:
            lossRate = self.lossCounter / self.frameNbr
            print("[*]RTP Packet Loss Rate: " + str(lossRate) +"\n")

    def pauseMovie(self):
        """Pause button handler."""
        self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY or self.state == self.SWITCHING :
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    def describeSession(self):
        """Describe button handler."""
        self.sendRtspRequest(self.DESCRIBE)

    def Switch(self):
        """Describe button handler."""
        self.sendRtspRequest(self.SWITCH)
        self.top = Toplevel(self.master)
        self.top.geometry("350x400")
        self.top.title("Choose movie")
        self.m1 = Button(self.top, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.m1["text"] = self.list_movie[0];
        self.m1["command"] =  self.choosemovie1
        self.m1.grid(row=1, column=4, padx=2, pady=2)

        self.m2 = Button(self.top, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.m2["text"] = self.list_movie[1];
        self.m2["command"] =  self.choosemovie2
        self.m2.grid(row=2, column=4, padx=2, pady=2)

        self.m3 = Button(self.top, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.m3["text"] = self.list_movie[2];
        self.m3["command"] =  self.choosemovie3
        self.m3.grid(row=3, column=4, padx=2, pady=2)      

        self.m4 = Button(self.top, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.m4["text"] = self.list_movie[3];
        self.m4["command"] =  self.choosemovie4
        self.m4.grid(row=4, column=4, padx=2, pady=2)

        self.m5 = Button(self.top, width=15, padx=3, pady=3, fg= "white", bg= "#264653",font=("Times", 11, 'bold'))
        self.m5["text"] = self.list_movie[4];
        self.m5["command"] =  self.choosemovie5
        self.m5.grid(row=5, column=4, padx=2, pady=2)

    def choosemovie1(self):
        if self.fileName != "video.mjpeg":
            self.fileName = "video.mjpeg"
            self.top.destroy()
            self.bytesReceived = 0
            self.startTime = 0
            self.lossCounter = 0
            self.frameNbr = 0
            self.setup["state"] = "normal"
            self.start["state"] = "disabled"
            self.pause["state"] = "disabled"
            self.teardown["state"] = "normal"
            self.describe["state"] = "disabled"
            self.switch["state"] = "normal"
            self.sessionId = 0
        else:
            self.top.destroy()
    def choosemovie2(self):
        if self.fileName != "video2.mjpeg":
            self.fileName = "video2.mjpeg"
            self.top.destroy()
            self.bytesReceived = 0
            self.startTime = 0
            self.lossCounter = 0
            self.frameNbr = 0
            self.setup["state"] = "normal"
            self.start["state"] = "disabled"
            self.pause["state"] = "disabled"
            self.teardown["state"] = "normal"
            self.describe["state"] = "disabled"
            self.switch["state"] = "normal"
            self.sessionId = 0
        else:
            self.top.destroy()
    def choosemovie3(self):
        if self.fileName != "video3.mjpeg":
            self.fileName = "video3.mjpeg"
            self.top.destroy()
            self.bytesReceived = 0
            self.startTime = 0
            self.lossCounter = 0
            self.frameNbr = 0
            self.setup["state"] = "normal"
            self.start["state"] = "disabled"
            self.pause["state"] = "disabled"
            self.teardown["state"] = "normal"
            self.describe["state"] = "disabled"
            self.switch["state"] = "normal"
            self.sessionId = 0
        else:
            self.top.destroy()
    def choosemovie4(self):
        if self.fileName != "video5.mjpeg":
            self.fileName = "video5.mjpeg"
            self.top.destroy()
            self.bytesReceived = 0
            self.startTime = 0
            self.lossCounter = 0
            self.frameNbr = 0
            self.setup["state"] = "normal"
            self.start["state"] = "disabled"
            self.pause["state"] = "disabled"
            self.teardown["state"] = "normal"
            self.describe["state"] = "disabled"
            self.switch["state"] = "normal"
            self.sessionId = 0
        else:
            self.top.destroy()
            
    def choosemovie5(self):
        if self.fileName != "movie.Mjpeg":
            self.fileName = "movie.Mjpeg"
            self.top.destroy()
            self.bytesReceived = 0
            self.startTime = 0
            self.lossCounter = 0
            self.frameNbr = 0  
            self.setup["state"] = "normal"
            self.start["state"] = "disabled"
            self.pause["state"] = "disabled"
            self.teardown["state"] = "normal"
            self.describe["state"] = "disabled"
            self.switch["state"] = "normal"
            self.sessionId = 0
        else:
            self.top.destroy()  
             
    def listenRtp(self):		
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    # Detect and count packet loss
                    if self.frameNbr + 1 != rtpPacket.seqNum():
                        self.lossCounter += (rtpPacket.seqNum() - (self.frameNbr + 1))
                        print("[*]Packet loss!")
                    # If sequence number doesn't match, we have a packet loss
                    currFrameNbr = rtpPacket.seqNum()
                    print("Current Seq Num: " + str(currFrameNbr))
                                        
                    if currFrameNbr > self.frameNbr: # Discard the late packet
                        # Count the received bytes
                        self.bytesReceived += len(rtpPacket.getPayload())
                        
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))  

                        currentTime = int(currFrameNbr * 0.05)
                        self.timeBox.configure(text="%02d:%02d" % (currentTime // 60, currentTime % 60))        

            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet(): 
                    break
                
                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break
                    
    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename
    
    def updateMovie(self, imageFile):
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image = photo, height=288) 
        self.label.image = photo
        
    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
    
    
    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""	
        #-------------
        # TO COMPLETE
        #-------------
        if requestCode == self.SETUP and (self.state == self.INIT or self.state == self.SWITCHING) :
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtspSeq = 1
            
            # Write the RTSP request to be sent.
            request = "SETUP " + str(self.fileName) + " RTSP/1.0\n"
            request += "CSeq: " + str(self.rtspSeq) + "\n"
            request += "Transport: RTP/UDP; client_port= " + str(self.rtpPort)
            
            # Keep track of the sent request.
            self.requestSent = self.SETUP

        # Play request
        elif requestCode == self.PLAY and (self.state == self.READY or self.state == self.SWITCHING) :
            # Update RTSP sequence number.
            self.rtspSeq += 1
            
            # Write the RTSP request to be sent.
            request = "PLAY " + str(self.fileName) + " RTSP/1.0\n"
            request += "CSeq: " + str(self.rtspSeq) + "\n"
            request += "Session: " + str(self.sessionId)
            
            # Keep track of the sent request.
            self.requestSent = self.PLAY
        
        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number.
            self.rtspSeq += 1
            
            # Write the RTSP request to be sent.
            request = "PAUSE " + str(self.fileName) + " RTSP/1.0\n"
            request += "CSeq: " + str(self.rtspSeq) + "\n"
            request += "Session: " + str(self.sessionId)
            
            # Keep track of the sent request.
            self.requestSent = self.PAUSE
            
        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            # Update RTSP sequence number.
            self.rtspSeq += 1
            
            # Write the RTSP request to be sent.
            request = "TEARDOWN " + str(self.fileName) + " RTSP/1.0\n"
            request += "CSeq: " + str(self.rtspSeq) + "\n"
            request += "Session: " + str(self.sessionId)
            
            # Keep track of the sent request.
            self.requestSent = self.TEARDOWN

        elif requestCode == self.DESCRIBE and not self.state == self.INIT:
            self.rtspSeq += 1

            request = "DESCRIBE " + str(self.fileName) + " RTSP/1.0\n"
            request += "CSeq: " + str(self.rtspSeq) + "\n"
            request += "Session: " + str(self.sessionId)
            # Keep track of the sent request.
            self.requestSent = self.DESCRIBE
        elif requestCode == self.SWITCH and self.state != self.PLAYING and self.state != self.INIT:
            self.rtspSeq += 1
            request = "SWITCH " + str(self.fileName) + " RTSP/1.0\n"
            request += "CSeq: " + str(self.rtspSeq) + "\n"
            request += "Session: " + str(self.sessionId)
            # Keep track of the sent request.
            self.requestSent = self.SWITCH
        else:
            return

        # Send the RTSP request using rtspSocket.
        self.rtspSocket.send(request.encode())
        print('\nData sent:\n' + request)
        
    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)
            
            if reply: 
                self.parseRtspReply(reply.decode("utf-8"))
            
            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break
    
    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        #TODO
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])
        
        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session
            print(self.sessionId)
            # Process only if the session ID is the same
            if self.sessionId == session:
                
                if int(lines[0].split(' ')[1]) == 200: 
                    
                    if self.requestSent == self.SETUP:
                        #-------------
                        # TO COMPLETE
                        #-------------
                        # Update RTSP state.
                        self.state = self.READY
                        
                        # Open RTP port.
                        self.openRtpPort() 

                        # Update buttons' states
                        self.setup["state"] = "disabled"
                        self.start["state"] = "normal"
                        self.pause["state"] = "disabled"
                        self.teardown["state"] = "normal"
                        self.describe["state"] = "normal"
                        self.switch["state"] = "normal"
                        

                    elif self.requestSent == self.PLAY:
                        # Update RTSP state.
                        self.state = self.PLAYING

                        # Start counting received bytes
                        self.startTime = time.time()
                        self.bytesReceived = 0

                        # Update buttons' states
                        self.setup["state"] = "disabled"
                        self.start["state"] = "disabled"
                        self.pause["state"] = "normal"
                        self.teardown["state"] = "normal"
                        self.switch["state"] = "disabled"

                    elif self.requestSent == self.PAUSE:
                        # Update RTSP state.
                        self.state = self.READY
                        
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()

                        # Calculate the video data rate
                        dataRate = int(self.bytesReceived / (time.time() - self.startTime))
                        print("[*]Video data rate: " + str(dataRate) + " bytes/sec\n")

                        # Update buttons' states
                        self.setup["state"] = "disabled"
                        self.start["state"] = "normal"
                        self.pause["state"] = "disabled"
                        self.teardown["state"] = "normal"
                        self.switch["state"] = "normal"
                    elif self.requestSent == self.TEARDOWN:
                        # Update RTSP state.
                        self.state = self.INIT
                        
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1 

                    elif self.requestSent == self.DESCRIBE:
                        # Write RTSP payload to session file
                        f = open(SESSION_FILE, "w")
                        for i in range(4, len(lines)):
                            f.write(lines[i] + '\n')
                        f.close()
                    elif self.requestSent == self.SWITCH:
                        # Write RTSP payload to session file
                        self.state = self.SWITCHING
                        index_popup = 0;
                        for i in range(4, len(lines)):
                           self.list_movie[index_popup] = lines[i]
                           index_popup = index_popup + 1

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        #-------------
        # TO COMPLETE
        #-------------
        # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)
        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(("0.0.0.0", self.rtpPort))
        except:
            tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure ?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            self.playMovie()
