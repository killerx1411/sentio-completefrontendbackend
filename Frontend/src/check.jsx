import { motion } from "framer-motion";

export default function StripeWave() {
  return (
    <div style={{ background: "#0a0f1c", padding: "60px" }}>
      <svg width="100%" height="200" viewBox="0 0 800 200">
        <defs>
          <linearGradient id="waveGradient" x1="0%" y1="0%" x2="200%" y2="0%">
            <stop offset="0%" stopColor="#4f46e5" />
            <stop offset="50%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#4f46e5" />
          </linearGradient>
        </defs>

        <motion.path
          d="M0 100 Q200 20 400 100 T800 100"
          fill="transparent"
          stroke="url(#waveGradient)"
          strokeWidth="3"
          animate={{
            pathLength: [0, 1],
            y: [0, -5, 0],
          }}
          transition={{
            pathLength: { duration: 2, ease: "easeInOut" },
            y: { duration: 3, repeat: Infinity, ease: "easeInOut" },
          }}
        />

        {/* moving gradient illusion */}
        <motion.rect
          x="0"
          y="0"
          width="800"
          height="200"
          fill="url(#waveGradient)"
          animate={{ x: [-800, 0] }}
          transition={{ repeat: Infinity, duration: 6, ease: "linear" }}
          style={{ opacity: 0.2 }}
        />
      </svg>
    </div>
  );
}