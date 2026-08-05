import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Float, Stars, MeshWobbleMaterial, Instance, Instances, Sky } from '@react-three/drei';
import * as THREE from 'three';

export default function RoleplayScene({ scenarioTitle }) {
  if (!scenarioTitle) return null;

  const titleLower = scenarioTitle.toLowerCase();
  
  if (titleLower.includes('coffee')) {
    return <CoffeeShopScene />;
  } else if (titleLower.includes('interview')) {
    return <InterviewScene />;
  } else if (titleLower.includes('airport') || titleLower.includes('flight')) {
    return <AirportScene />;
  } else if (titleLower.includes('trip') || titleLower.includes('road')) {
    return <RoadTripScene />;
  }

  // Fallback abstract scene for unknown scenarios
  return <DefaultScene />;
}

// ── Coffee Shop ────────────────────────────────────────────────────────
function CoffeeShopScene() {
  return (
    <>
      <color attach="background" args={['#2c1810']} />
      <ambientLight intensity={0.6} />
      <pointLight position={[0, 5, 0]} color="#ffb07c" intensity={2} />
      
      <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
        <mesh position={[-3, 0, -5]}>
          <cylinderGeometry args={[1, 1, 2.5, 32]} />
          <meshStandardMaterial color="#8b5a2b" />
        </mesh>
      </Float>
      
      <Float speed={1.5} rotationIntensity={1} floatIntensity={2}>
        <mesh position={[3, 1, -8]}>
          <torusGeometry args={[0.8, 0.2, 16, 100]} />
          <meshStandardMaterial color="#e6c280" />
        </mesh>
      </Float>
      
      {/* Steam particles */}
      <Particles count={50} color="#ffffff" size={0.5} speed={1.2} />
    </>
  );
}

// ── Job Interview ──────────────────────────────────────────────────────
function InterviewScene() {
  return (
    <>
      <color attach="background" args={['#0f172a']} />
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 10, 5]} color="#38bdf8" intensity={1.5} />
      
      {/* Abstract Tech Grid/Cubes */}
      <group position={[0, 0, -10]}>
        {Array.from({ length: 15 }).map((_, i) => (
          <Float key={i} speed={1} rotationIntensity={0.2} floatIntensity={0.5}>
            <mesh position={[(Math.random() - 0.5) * 20, (Math.random() - 0.5) * 10, (Math.random() - 0.5) * 10]}>
              <boxGeometry args={[1.5, 1.5, 1.5]} />
              <meshStandardMaterial color="#0284c7" wireframe={i % 3 === 0} />
            </mesh>
          </Float>
        ))}
      </group>
    </>
  );
}

// ── Airport ────────────────────────────────────────────────────────────
function AirportScene() {
  return (
    <>
      <Sky distance={450000} sunPosition={[0, 1, 0]} inclination={0} azimuth={0.25} />
      <ambientLight intensity={1} />
      
      {/* Fast moving clouds/planes abstractly */}
      <Particles count={200} color="#ffffff" size={0.8} speed={3} direction="horizontal" />
    </>
  );
}

// ── Road Trip ──────────────────────────────────────────────────────────
function RoadTripScene() {
  return (
    <>
      <color attach="background" args={['#4c1d95']} /> {/* Deep purple sky */}
      <ambientLight intensity={0.5} />
      <pointLight position={[0, 0, -20]} color="#f97316" intensity={10} distance={50} /> {/* Sunset */}
      
      {/* Sunset sun */}
      <mesh position={[0, 0, -30]}>
        <sphereGeometry args={[8, 32, 32]} />
        <meshBasicMaterial color="#f97316" />
      </mesh>
      
      {/* Fast passing lines simulating driving */}
      <Particles count={100} color="#fcd34d" size={0.3} speed={5} direction="z" />
    </>
  );
}

// ── Default ────────────────────────────────────────────────────────────
function DefaultScene() {
  return (
    <>
      <color attach="background" args={['#1e1b4b']} />
      <ambientLight intensity={0.8} />
      <Stars radius={100} depth={50} count={3000} factor={4} fade speed={1.5} />
      <Float speed={2} rotationIntensity={2} floatIntensity={1.5}>
        <mesh position={[0, 0, -10]}>
          <icosahedronGeometry args={[2, 0]} />
          <MeshWobbleMaterial color="#8b5cf6" factor={0.4} speed={2} />
        </mesh>
      </Float>
    </>
  );
}

// ── Utility: Particles ─────────────────────────────────────────────────
function Particles({ count = 100, color = "#ffffff", size = 0.5, speed = 1, direction = "vertical" }) {
  const mesh = useRef();
  
  const particles = useMemo(() => {
    const temp = [];
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * 30;
      const y = (Math.random() - 0.5) * 30;
      const z = (Math.random() - 0.5) * 30;
      temp.push({ position: new THREE.Vector3(x, y, z), factor: Math.random() + 0.5 });
    }
    return temp;
  }, [count]);

  const dummy = useMemo(() => new THREE.Object3D(), []);

  useFrame((state) => {
    particles.forEach((particle, i) => {
      let { x, y, z } = particle.position;
      
      const t = state.clock.getElapsedTime() * speed * particle.factor;
      
      if (direction === "vertical") y = (y + t) % 30 - 15;
      else if (direction === "horizontal") x = (x + t) % 30 - 15;
      else if (direction === "z") z = (z + t) % 30 - 15;

      dummy.position.set(x, y, z);
      dummy.updateMatrix();
      mesh.current.setMatrixAt(i, dummy.matrix);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={mesh} args={[null, null, count]}>
      <sphereGeometry args={[size, 8, 8]} />
      <meshBasicMaterial color={color} transparent opacity={0.6} />
    </instancedMesh>
  );
}
