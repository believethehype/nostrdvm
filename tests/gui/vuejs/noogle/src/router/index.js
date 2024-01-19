import { createWebHistory, createRouter } from "vue-router";



const routes = [
  { path: "/", component: () => import("@/components/Home.vue") },
  { path: "/about", component: () => import("@/components/AboutPage.vue") },
  { path: "/donate", component: () => import("@/components/Donate.vue") },
  { path: "/test", component: () => import("@/components/Donate.vue") },
  { path: "/article/:id", component: () => import("@/components/Home.vue") },
  { path: '/:pathMatch(.*)*', component: () => import("@/components/Home.vue") },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;