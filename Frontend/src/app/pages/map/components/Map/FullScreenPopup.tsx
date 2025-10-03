import React from 'react';
import './styles.css';

interface FullScreenPopupProps {
  bank: {
    sucursal_nombre: string;
    calle: string;
    altura: number;
    // Agrega más campos si es necesario
  };
  onClose: () => void;
}

const FullScreenPopup: React.FC<FullScreenPopupProps> = ({ bank, onClose }) => {
  return (
    <div className="fullscreen-popup-overlay map-area-overlay">
      <div className="fullscreen-popup-content">
        <button className="close-btn" onClick={onClose}>Cerrar</button>
        <h2>{bank.sucursal_nombre}</h2>
        <p>{bank.calle} {bank.altura}</p>
        {/* Agrega más información aquí si es necesario */}
      </div>
    </div>
  );
};

export default FullScreenPopup;

