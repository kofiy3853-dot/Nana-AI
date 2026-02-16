import React, { useState, useEffect } from 'react';
import App from './App';
import Login from './Login';
import './login.css';

const AuthWrapper = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Check if user has a valid token
        const token = localStorage.getItem('nana-token');
        const expiry = localStorage.getItem('nana-token-expiry');

        if (token && expiry) {
            const now = Date.now();
            if (now < parseInt(expiry)) {
                setIsAuthenticated(true);
            } else {
                // Token expired, clear it
                localStorage.removeItem('nana-token');
                localStorage.removeItem('nana-token-expiry');
            }
        }

        setIsLoading(false);
    }, []);

    const handleLogin = (token) => {
        setIsAuthenticated(true);
    };

    const handleLogout = () => {
        localStorage.removeItem('nana-token');
        localStorage.removeItem('nana-token-expiry');
        setIsAuthenticated(false);
    };

    if (isLoading) {
        return (
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100vh',
                background: 'var(--bg-primary)'
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div className="nana-status-dot active" style={{ margin: '0 auto 1rem' }}>
                        <svg width="10" height="10" viewBox="0 0 10 10">
                            <circle cx="5" cy="5" r="5" fill="white" />
                        </svg>
                    </div>
                    <p style={{ color: 'var(--text-secondary)' }}>Loading...</p>
                </div>
            </div>
        );
    }

    return isAuthenticated ? <App onLogout={handleLogout} /> : <Login onLogin={handleLogin} />;
};

export default AuthWrapper;
