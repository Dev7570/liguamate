import { Suspense, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Sphere, MeshDistortMaterial } from '@react-three/drei';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/landing.css';

function AnimatedSphere() {
  const meshRef = useRef();
  
  useFrame((state) => {
    meshRef.current.rotation.x = state.clock.getElapsedTime() * 0.2;
    meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.3;
  });

  return (
    <Sphere ref={meshRef} visible args={[1, 100, 200]} scale={1.8} position={[1.5, 0, -1]}>
      <MeshDistortMaterial
        color="#7c3aed"
        attach="material"
        distort={0.4}
        speed={1.5}
        roughness={0.2}
      />
    </Sphere>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      {/* 3D Background */}
      <div className="landing-canvas-container">
        <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
          <color attach="background" args={['#0F172A']} /> {/* Slate 900 match */}
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <pointLight position={[-10, -10, -5]} intensity={0.5} color="#3b82f6" />
          
          <Suspense fallback={null}>
            <AnimatedSphere />
            <Stars 
              radius={100} 
              depth={50} 
              count={5000} 
              factor={4} 
              saturation={0} 
              fade 
              speed={1} 
            />
          </Suspense>
          
          <OrbitControls 
            enableZoom={false} 
            enablePan={false}
            autoRotate
            autoRotateSpeed={0.5}
          />
        </Canvas>
      </div>

      {/* UI Overlay */}
      <div className="landing-overlay">
        <header className="landing-header">
          <Link to="/" className="landing-logo">
            <div className="landing-logo-icon">🌟</div>
            <span className="landing-logo-text">LinguaMate</span>
          </Link>
          <div className="landing-nav">
            <button className="btn landing-secondary-btn" onClick={() => navigate('/login')}>
              Login
            </button>
            <button className="btn btn-primary" onClick={() => navigate('/signup')}>
              Sign Up
            </button>
          </div>
        </header>

        <main className="landing-hero">
          <div className="landing-badge">✨ Next-Gen AI Language Learning</div>
          <h1 className="landing-title">
            Master languages with <span>AI conversations</span> and interactive games.
          </h1>
          <p className="landing-subtitle">
            Immerse yourself in real-time roleplay, earn achievements, and build your vocabulary with intelligent, personalized AI interactions.
          </p>
          <div className="landing-cta-group">
            <button className="btn btn-primary btn-lg" onClick={() => navigate('/signup')}>
              Start Learning Now
            </button>
            <button className="btn landing-secondary-btn btn-lg" onClick={() => navigate('/login')}>
              I already have an account
            </button>
          </div>
        </main>

        <div className="landing-interactive-hint">
          <span>Interact with background</span>
          <div className="hint-mouse">
            <div className="hint-wheel" />
          </div>
        </div>
      </div>
    </div>
  );
}
