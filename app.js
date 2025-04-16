console.log('app.js loaded');

   // Use environment variable or fallback to localhost for development
   const BACKEND_URL = window.BACKEND_URL || 'http://localhost:5000';
   const socket = io(BACKEND_URL);

   socket.on('connect', () => {
       console.log('Connected to server');
       document.getElementById('statusMessage').textContent = 'Connected to painting server';
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
       // Clear status message after 5 seconds
       setTimeout(() => {
           statusMessage.textContent = '';
       }, 5000);
   });

   socket.on('error', (data) => {
       console.log('Error from server:', data.message);
       document.getElementById('statusMessage').textContent = data.message;
       if (data.message.includes('Webcam')) {
           alert('Please ensure your webcam is connected and permissions are granted.');
       }
   });

   socket.on('disconnect', () => {
       console.log('Disconnected from server');
       document.getElementById('statusMessage').textContent = 'Disconnected from server';
   });

   // Save button event listener
   document.getElementById('saveButton').addEventListener('click', () => {
       console.log('Emitting save_canvas');
       socket.emit('save_canvas');
       document.getElementById('statusMessage').textContent = 'Saving canvas...';
   });