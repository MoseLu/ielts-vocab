export function buildDictationFeedback(answer: string, expected: string) {
  const submitted = answer.trim() || '未输入'
  return `拼写不一致：你输入「${submitted}」，正确拼写「${expected}」。请重听发音后再写一遍。`
}
