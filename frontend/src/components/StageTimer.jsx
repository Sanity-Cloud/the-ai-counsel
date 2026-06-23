import { useState, useEffect } from 'react';

export default function StageTimer({ startTime, endTime, label = "Elapsed" }) {
    const [elapsed, setElapsed] = useState(0);

    useEffect(() => {
        if (!startTime || endTime) return;

        // Active timer
        const interval = setInterval(() => {
            setElapsed(Date.now() - startTime);
        }, 100); // Update every 100ms for smoothness

        return () => clearInterval(interval);
    }, [startTime, endTime]);

    if (!startTime) return null;

    const displayElapsed = endTime ? (endTime - startTime) : elapsed;

    const formatTime = (ms) => {
        const seconds = (ms / 1000).toFixed(1);
        return `${seconds}s`;
    };

    return (
        <span className="stage-timer" style={{
            marginLeft: '10px',
            fontSize: '12px',
            color: '#666',
            fontFamily: 'monospace'
        }}>
            {label}: {formatTime(displayElapsed)}
        </span>
    );
}
