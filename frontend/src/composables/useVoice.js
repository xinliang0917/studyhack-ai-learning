// Global speech synthesis utility
let utterance = null
let _warmedUp = false

function warmup() {
  if (_warmedUp || !('speechSynthesis' in window)) return
  _warmedUp = true
  // Chrome bug: first speak() has 1-3s delay.
  // Must use non-empty text + non-zero volume, otherwise Chrome ignores the warmup.
  try {
    window.speechSynthesis.getVoices()
    // Speak a tiny character and immediately cancel - this forces Chrome to initialize
    const u = new SpeechSynthesisUtterance()
    u.text = '.'
    u.volume = 0.01
    window.speechSynthesis.speak(u)
    window.speechSynthesis.cancel()
    // Some Chrome versions need a second pass
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(''))
    window.speechSynthesis.cancel()
  } catch(e) {}
}
// Pre-warm speech engine early
if (typeof window !== 'undefined') {
  if (document.readyState === 'complete') { warmup() }
  else { window.addEventListener('load', warmup, { once: true }) }
  document.addEventListener('click', warmup, { once: true })
}

let _isMuted = false
export function toggleMute() {
  _isMuted = !_isMuted
  if (_isMuted) cancelSpeech()
  return _isMuted
}
export function isMuted() { return _isMuted }

export function speak(text, { rate = 1.0, pitch = 1.0 } = {}) {
  if (_isMuted) return
  if ('speechSynthesis' in window) {
    warmup()
    window.speechSynthesis.cancel()
    utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    utterance.rate = rate
    utterance.pitch = pitch
    window.speechSynthesis.speak(utterance)
  }
}

export function cancelSpeech() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
}

export function speakExamResult(result) {
  if (!result) return
  const msg = '得分 ' + result.score + ' 分，共 ' + result.total + ' 题，正确 ' + result.correct + ' 题'
  speak(msg)
}

export function speakQuizGenerated(total, timeLimit) {
  const minutes = Math.round((timeLimit || 0) / 60)
  let msg = '测验已生成，共 ' + total + ' 道题'
  if (minutes > 0) msg += '，限时 ' + minutes + ' 分钟'
  speak(msg)
}

export function speakQuestion(q, index, total) {
  let msg = '第 ' + (index + 1) + ' 题，共 ' + total + ' 题。'
  msg += (q.question_text || q.question || "")
  if (q.options) {
    for (const [key, value] of Object.entries(q.options)) {
      msg += '，选项 ' + key + '：' + value
    }
  }
  speak(msg)
}
