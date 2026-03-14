import React from 'react'

function Toast({ message, type = 'info' }) {
  return (
    <div className={`toast toast-${type}`}>
      {message}
    </div>
  )
}

export default Toast