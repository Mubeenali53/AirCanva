console.log('app.js loaded');

   const BACKEND_URL = window.BACKEND_URL || 'http://localhost:5000';
   const socket = io(BACKEND_URL);

   // Webcam setup
   const video = document.getElementById('webcamVideo');
   const canvas = document.getElementById('webcamCanvas');
   const ctx = canvas.getContext('2d');
   let isStreaming = false;

   async function startWebcam() {
       try {
           const stream = await navigator.mediaDevices.getUserMedia({
               video: { width: 640, height: 480 },
               audio: false
           });
           video.srcObject = stream;
           video.play();
           canvas.width = 640;
           canvas.height = 480;
           isStreaming = true;
           sendFrames();
           console.log('Webcam started');
           document.getElementById('statusMessage').textContent = 'Webcam connected';
       } catch (err) {
           console.error('Webcam error:', err);
           document.getElementById('statusMessage').textContent = 'Failed to access webcam';
           alert('Please allow webcam access.');
       }
   }

   function sendFrames() {
       if (!isStreaming) return;
       // Capture frame from video
       ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
       const frameData = canvas.toDataURL('image/jpeg', 0.8); // JPEG at 80% quality
       const base64Data = frameData.split(',')[1]; // Remove "data:image/jpeg;base64,"
       socket.emit('webcam_frame', { image: base64Data });
       // Send frames at ~10 FPS
       setTimeout(sendFrames, 100);
   }

   // Start webcam when connected to server
   socket.on('connect', () => {
       console.log('Connected to server');
       document.getElementById('statusMessage').textContent = 'Connected to painting server';
       startWebcam();
   });

   socket.on('canvas_frame', (data) => {
       console.log('Received canvas frame');
       const canvasImage = document.getElementById('canvasImage');
       canvasImage.src = 'data:image/jpeg;base64,' + data.image;
   });

   socket.on('save_status', (data) => {
       console.log('Save status:', data.message);
       const statusMessage = document.getElementById('statusMessage');
       statusMessage.textContent = data.message;
       setTimeout(() => {
           statusMessage.textContent = '';
       }, 5000);
   });

   socket.on('error', (data) => {
       console.log('Error from server:', data.message);
       document.getElementById('statusMessage').textContent = data.message;
       alert(data.message);
   });

   socket.on('disconnect', () => {
       console.log('Disconnected from server');
       document.getElementById('statusMessage').textContent = 'Disconnected from server';
       isStreaming = false;
       if (video.srcObject) {
           video.srcObject.getTracks().forEach(track => track.stop());
       }
   });

   // Save button
   document.getElementById('saveButton').addEventListener('click', () => {
       console.log('Emitting save_canvas');
       socket.emit('save_canvas');
       document.getElementById('statusMessage').textContent = 'Saving canvas...';
   });