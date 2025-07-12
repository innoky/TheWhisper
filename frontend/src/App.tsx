import { useState } from 'react';

function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const outerBg = theme === 'light' ? 'bg-blue-100' : 'bg-gray-900';
  const innerBg = theme === 'light' ? '#fff' : '#1f2937';
  const textColor = theme === 'light' ? '#1f2937' : '#fff';

  return (
    <div className={`${outerBg} min-h-screen flex items-center justify-center transition-colors duration-500`}>
      <div className="w-[90vw] h-[90vh] flex flex-col items-center justify-center">
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          className="block"
          style={{ width: '100%', height: '100%' }}
        >
          <path
            d="
              M 5 15
              Q 5 5 20 10
              Q 50 -10 80 10
              Q 95 5 95 15
              L 95 90
              L 5 90
              Z
            "
            fill={innerBg}
            stroke="#e0eaff"
            strokeWidth="1"
          />
          <text
            x="50%"
            y="22%"
            textAnchor="middle"
            fontSize="10"
            fontWeight="bold"
            fill={textColor}
            style={{ fontFamily: 'sans-serif', userSelect: 'none' }}
          >
            THE WHISPER
          </text>
        </svg>
        {/* Контент под SVG */}
        <div className="-mt-16 flex flex-col items-center justify-center w-full max-w-4xl">
          <button
            className="mb-8 px-4 py-2 rounded bg-blue-300 hover:bg-blue-400 transition"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          >
            {theme === 'light' ? 'Включить тёмную тему' : 'Включить светлую тему'}
          </button>
          <h1 className="text-2xl font-bold">Контент</h1>
        </div>
      </div>
    </div>
  );
}

export default App;
