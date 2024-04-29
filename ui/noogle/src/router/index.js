import { createWebHistory, createRouter } from "vue-router";



const routes = [
  { path: "/", component: () => import("@/components/Home.vue") },
  { path: "/about", component: () => import("@/components/AboutPage.vue") },
  { path: "/donate", component: () => import("@/components/Donate.vue") },
  { path: "/nip89", component: () => import("@/components/Nip89view.vue") },
  { path: "/image", component: () => import("@/components/Image.vue") },
  { path: "/filter", component: () => import("@/components/FilterGeneration.vue") },

  { path: "/discover", component: () => import("@/components/RecommendationGeneration.vue") },
  { path: "/article/:id", component: () => import("@/components/Home.vue") },
  { path: '/:pathMatch(.*)*', component: () => import("@/components/Home.vue") },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;