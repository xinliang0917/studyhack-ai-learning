import { createRouter, createWebHistory } from "vue-router"

const routes = [
  { path: "/login", name: "Login", component: () => import("../views/Login.vue") },
  { path: "/register", name: "Register", component: () => import("../views/Register.vue") },
  { path: "/", redirect: "/dashboard" },
  { path: "/dashboard", name: "Dashboard", component: () => import("../views/Dashboard.vue"), meta: { requiresAuth: true } },
  { path: "/knowledge", name: "KnowledgeBase", component: () => import("../views/KnowledgeBase.vue"), meta: { requiresAuth: true } },
  { path: "/rag", name: "RagChat", component: () => import("../views/RagChat.vue"), meta: { requiresAuth: true } },
  { path: "/schedule", name: "Schedule", component: () => import("../views/Schedule.vue"), meta: { requiresAuth: true } },
  { path: "/knowledge-graph", name: "KnowledgeGraph", component: () => import("../views/KnowledgeGraph.vue"), meta: { requiresAuth: true } },
  { path: "/course", name: "CourseOutline", component: () => import("../views/CourseOutline.vue"), meta: { requiresAuth: true } },
  { path: "/course/:outlineId/chapter/:chapterId", name: "ChapterLearning", component: () => import("../views/ChapterLearning.vue"), meta: { requiresAuth: true } },
  { path: "/quiz", name: "Quiz", component: () => import("../views/Quiz.vue"), meta: { requiresAuth: true } },
  { path: "/exam/:examId", name: "Exam", component: () => import("../views/Exam.vue"), meta: { requiresAuth: true } },
  { path: "/wrong-questions", name: "WrongQuestions", component: () => import("../views/WrongQuestions.vue"), meta: { requiresAuth: true } },
  { path: "/settings", name: "Settings", component: () => import("../views/Settings.vue"), meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("token")
  if (to.meta.requiresAuth && !token) {
    next("/login")
  } else {
    next()
  }
})

export default router
