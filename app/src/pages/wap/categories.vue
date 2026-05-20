<template>
  <div class="wap-page">
    <wap-header />
    <main class="wap-main">
      <h2 class="wap-page-title">{{ $t('nav.categories') }}</h2>
      <div class="category-tabs">
        <span
          v-for="(cat, idx) in categories"
          :key="cat.name"
          class="category-tab"
          :class="{ active: activeTab === idx }"
          @click="selectCategory(idx)"
        >
          {{ cat.name }} ({{ cat.count }})
        </span>
      </div>
      <wap-book-cards :books="books" />
      <div v-if="page_cnt > 1" class="wap-pagination">
        <button @click="prevPage" :disabled="page === 1">←</button>
        <span>{{ page }} / {{ page_cnt }}</span>
        <button @click="nextPage" :disabled="page === page_cnt">→</button>
      </div>
    </main>
    <wap-footer />
  </div>
</template>

<script>
import WapHeader from '~/components/WapHeader.vue';
import WapFooter from '~/components/WapFooter.vue';
import WapBookCards from '~/components/WapBookCards.vue';

export default {
  layout: 'wap',
  components: {
    WapHeader,
    WapFooter,
    WapBookCards
  },
  data() {
    return {
      activeTab: 0,
      categories: [],
      books: [],
      page: 1,
      page_size: 60,
      total: 0,
      page_cnt: 0,
      loading: false
    };
  },
  async created() {
    await this.initUserInfo();
    await this.fetchCategories();
  },
  methods: {
    async initUserInfo() {
      try {
        const rsp = await this.$backend('/user/info');
        if (rsp.err === 'ok') {
          this.$store.commit('login', rsp);
        }
      } catch (e) {
        console.error(e);
      }
    },
    async fetchCategories() {
      try {
        const rsp = await this.$backend('/categories');
        if (rsp.err === 'ok') {
          this.categories = rsp.categories || [];
          if (this.categories.length > 0) {
            await this.fetchBooks();
          }
        }
      } catch (e) {
        console.error(e);
      }
    },
    async fetchBooks() {
      if (this.categories.length === 0) return;

      this.loading = true;
      const category = this.categories[this.activeTab].name;
      const start = (this.page - 1) * this.page_size;
      const query = `#category:=${category}`;

      try {
        const rsp = await this.$backend(`/search?name=${encodeURIComponent(query)}&start=${start}&size=${this.page_size}&order=title`);
        if (rsp.err === 'ok') {
          this.books = rsp.books || [];
          this.total = rsp.total || 0;
          this.page_cnt = Math.max(1, Math.ceil(this.total / this.page_size));
        }
      } catch (e) {
        console.error(e);
      } finally {
        this.loading = false;
      }
    },
    selectCategory(idx) {
      this.activeTab = idx;
      this.page = 1;
      this.fetchBooks();
    },
    prevPage() {
      if (this.page > 1) {
        this.page--;
        this.fetchBooks();
      }
    },
    nextPage() {
      if (this.page < this.page_cnt) {
        this.page++;
        this.fetchBooks();
      }
    }
  }
};
</script>

<style scoped>
.wap-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
}
.wap-page-title {
  text-align: center;
}
.category-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 16px;
}
.category-tab {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
}
.category-tab.active {
  background-color: #2196F3;
  color: white;
  border-color: #2196F3;
}
.wap-pagination {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
}
.wap-pagination button {
  padding: 6px 12px;
}
</style>
