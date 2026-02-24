import React from 'react';
import { motion } from 'framer-motion';

// simple reusable animation variants
const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } }
};
const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } }
};

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 text-gray-800">
      {/* topbar */}
      <motion.header
        className="fixed top-0 left-0 right-0 h-16 bg-white shadow-md flex items-center justify-between px-6 z-20"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0, transition: { duration: 0.3 } }}
      >
        <div className="font-semibold text-lg">AssessmentSys</div>
        <div className="flex items-center gap-4">
          <button className="relative p-2 rounded-full hover:bg-gray-200 transition">
            🔔
          </button>
          <button className="p-2 rounded-full hover:bg-gray-200 transition">👤</button>
        </div>
      </motion.header>

      {/* sidebar */}
      <motion.nav
        className="fixed top-16 left-0 w-60 bg-white h-[calc(100vh-4rem)] shadow-sm overflow-auto"
        initial={{ x: -200 }}
        animate={{ x: 0, transition: { type: 'spring', stiffness: 300, damping: 30 } }}
      >
        <ul className="mt-4 space-y-1">
          {['Overview', 'Candidates', 'Assessments', 'Results', 'Reports', 'Security', 'Settings'].map(item => (
            <motion.li
              key={item}
              variants={fadeUp}
              whileHover={{ x: 5 }}
              className="px-4 py-2 cursor-pointer hover:bg-indigo-100 rounded-md"
            >
              {item}
            </motion.li>
          ))}
        </ul>
      </motion.nav>

      {/* main content */}
      <main className="pt-20 pl-64 p-6">
        <motion.section
          className="mb-12"
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
        >
          <div className="flex flex-wrap gap-6">
            {['Total Candidates 1,234', 'Active Assessments 12', 'Completed Tests 458', 'Pass Rate 78%'].map((text, i) => (
              <motion.div key={i} variants={fadeUp} className="bg-white rounded-xl shadow-lg p-6 flex-1 min-w-[200px]">
                <p className="text-sm text-gray-500">{text.split(' ')[0]}</p>
                <h3 className="text-2xl font-bold mt-1">{text.split(' ').slice(1).join(' ')}</h3>
              </motion.div>
            ))}
          </div>
        </motion.section>

        <motion.section
          className="mb-12"
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
        >
          <h2 className="text-xl font-semibold mb-4">Assessment Trends</h2>
          <div className="h-64 bg-white rounded-xl shadow-lg flex items-center justify-center">
            {/* chart placeholder; an actual chart library like chart.js can be integrated */}
            <span className="text-gray-400">[Chart animates here]</span>
          </div>
        </motion.section>
      </main>
    </div>
  );
}
