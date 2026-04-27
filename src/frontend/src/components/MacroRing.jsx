/**
 * MacroRing — four SVG circular progress rings showing consumed vs. goal.
 *
 * Color coding per ring:
 *   green  — at or under goal
 *   yellow — within 10 % over goal
 *   red    — more than 10 % over goal
 */

const CIRCUMFERENCE = 2 * Math.PI * 42   // r = 42, viewBox 100×100

const MACROS = [
  { key: 'calories',  label: 'Calories',    unit: 'kcal', color: '#3b82f6' },
  { key: 'protein_g', label: 'Protein',     unit: 'g',    color: '#22c55e' },
  { key: 'carbs_g',   label: 'Carbs',       unit: 'g',    color: '#f97316' },
  { key: 'fat_g',     label: 'Fat',         unit: 'g',    color: '#a855f7' },
]

function Ring({ label, unit, value, goal, baseColor }) {
  const pct   = goal > 0 ? value / goal : 0
  const fill  = Math.min(pct, 1) * CIRCUMFERENCE
  const color = pct > 1.10 ? '#ef4444' : pct > 1.00 ? '#f59e0b' : baseColor

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-24 h-24">
        {/* SVG rotated -90° so progress starts at 12 o'clock */}
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          {/* Background track */}
          <circle cx="50" cy="50" r="42" fill="none" stroke="#e5e7eb" strokeWidth="10" />
          {/* Progress arc */}
          <circle
            cx="50" cy="50" r="42"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${fill} ${CIRCUMFERENCE}`}
            style={{ transition: 'stroke-dasharray 0.4s ease, stroke 0.3s ease' }}
          />
        </svg>
        {/* Center text — counter-rotated to stay upright */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-sm font-bold leading-none">{Math.round(value)}</span>
          <span className="text-xs text-gray-400">/{goal}</span>
        </div>
      </div>
      <p className="text-xs font-medium text-gray-600 text-center">{label}<br/><span className="text-gray-400">{unit}</span></p>
    </div>
  )
}

export default function MacroRing({ totals = {}, goals = {} }) {
  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
        Today's Progress
      </h2>
      <div className="grid grid-cols-4 gap-4">
        {MACROS.map(({ key, label, unit, color }) => (
          <Ring
            key={key}
            label={label}
            unit={unit}
            value={totals[key] ?? 0}
            goal={goals[key]   ?? 1}
            baseColor={color}
          />
        ))}
      </div>
    </div>
  )
}
