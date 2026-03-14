import React from 'react'
import { useNavigate } from 'react-router-dom'

function HomePage({ user, currentDay, onStartPractice, onDayChange }) {
  const navigate = useNavigate()

  const handleDayClick = (day) => {
    onDayChange(day)
    navigate('/practice')
  }

  return (
    <div className="home-page">
      <h1 className="page-title">选择学习日期</h1>
      <p className="page-subtitle">每天100个单词，30天搞定雅思词汇</p>
      <div className="day-grid">
        {Array.from({ length: 30 }, (_, i) => {
          const day = i + 1
          const isActive = currentDay === day
          return (
            <div
              key={day}
              className={`day-card ${isActive ? 'active' : ''}`}
              onClick={() => handleDayClick(day)}
            >
              <div className="day-number">Day {day}</div>
              <div className="day-words">100 words</div>
              {isActive && <div className="day-indicator">当前</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default HomePage