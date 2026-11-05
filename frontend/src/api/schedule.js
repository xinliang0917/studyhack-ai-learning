import api from "./index"

export const listSchedule = (params) => api.get("/schedule/items", { params })

export const createSchedule = (data) => api.post("/schedule/items", data)

export const updateSchedule = (id, data) => api.put(`/schedule/items/${id}`, data)

export const toggleSchedule = (id) => api.patch(`/schedule/items/${id}/toggle`)

export const deleteSchedule = (id) => api.delete(`/schedule/items/${id}`)

export const getScheduleStats = () => api.get("/schedule/stats")

export const autoPlan = (outlineId, days = 7, startDate = null) =>
  api.post("/schedule/auto-plan", {
    outline_id: outlineId,
    days,
    start_date: startDate,
  })
