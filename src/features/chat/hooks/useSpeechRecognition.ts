import { useEffect, useRef, useState } from 'react';

export function useSpeechRecognition() {
  const [isListening, setIsListening] = useState(false);
  const recognition = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      recognition.current = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
      recognition.current.continuous = false;
      recognition.current.interimResults = false;
    }
  }, []);

  const startListening = (onResult: (transcript: string) => void) => {
    if (!recognition.current) {
      alert('Speech recognition is not supported in your browser.');
      return;
    }

    recognition.current.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      onResult(transcript);
      setIsListening(false);
    };

    recognition.current.onerror = () => {
      setIsListening(false);
    };

    recognition.current.onend = () => {
      setIsListening(false);
    };

    recognition.current.start();
    setIsListening(true);
  };

  const stopListening = () => {
    if (recognition.current) {
      recognition.current.stop();
      setIsListening(false);
    }
  };

  return { isListening, startListening, stopListening };
}