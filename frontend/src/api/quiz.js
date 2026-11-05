import api from "./index"

export const generateQuiz = (chapterIds, count = 5, difficulty = 'medium', timeLimit = 1800) =>
  api.post('/quiz/generate', { chapter_ids: chapterIds, count, difficulty, time_limit: timeLimit })

export const generateQuizByCourse = (outlineId, count = 5, difficulty = 'medium', timeLimit = 1800) =>
  api.post('/quiz/generate-by-course', { outline_id: outlineId, count, difficulty, time_limit: timeLimit })

export const submitExam = (examId, answers) => api.post(`/quiz/${examId}/submit`, { exam_id: examId, answers })

export const getExamHistory = () => api.get('/quiz/history')

export const deleteExam = (examId) => api.delete(`/quiz/${examId}`)

export const getWrongQuestions = (chapterId, difficulty) =>
  api.get('/quiz/wrong-questions', { params: { chapter_id: chapterId || undefined, difficulty: difficulty || undefined } })

export const practiceWrongQuestions = (chapterId, difficulty) =>
  api.post('/quiz/wrong-questions/practice', null, { params: { chapter_id: chapterId || undefined, difficulty: difficulty || undefined } })

export const getLearningStats = () => api.get('/quiz/progress/stats')

export const getWrongStats = () => api.get('/quiz/wrong-questions/stats')


export const getExamQuestions = (examId) => api.get('/quiz/' + examId + '/questions')

export const getReviewQueue = (limit = 20) =>
  api.get('/quiz/wrong-questions/review', { params: { limit } })

export const reviewWrongQuestion = (questionId, quality) =>
  api.post(`/quiz/wrong-questions/${questionId}/review`, { quality })

export const explainWrongQuestion = (questionId) =>
  api.post(`/quiz/wrong-questions/${questionId}/explain`)