<template>
  <div class="wap-page">
    <wap-header />
    <main class="wap-main">
      <h2 class="wap-page-title">{{ $t('listMeta.allLanguages') }}</h2>
      <div class="meta-tags">
        <span
          v-for="item in meta_items"
          :key="item.name"
          class="meta-tag"
          @click="selectLanguage(item.name)"
        >
          {{ item.name }} ({{ item.count }})
        </span>
      </div>
      <div v-if="selectedLanguage" class="selected-language">
        <h3>{{ selectedLanguage }}</h3>
        <wap-book-cards :books="books" />
        <div v-if="page_cnt > 1" class="wap-pagination">
          <button @click="prevPage" :disabled="page === 1">←</button>
          <span>{{ page }} / {{ page_cnt }}</span>
          <button @click="nextPage" :disabled="page === page_cnt">→</button>
        </div>
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
      items: [],
      total: 0,
      selectedLanguage: '',
      books: [],
      page: 1,
      page_size: 60,
      total_books: 0,
      page_cnt: 0,
      loading: false
    };
  },
  computed: {
    meta_items() {
      return this.items;
    }
  },
  async created() {
    await this.initUserInfo();
    await this.fetchLanguages();
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
    async fetchLanguages() {
      try {
        const rsp = await this.$backend('/language?show=all');
        if (rsp.err === 'ok') {
          this.items = rsp.items;
          this.total = rsp.total;
        }
      } catch (e) {
        console.error(e);
      }
    },
    async selectLanguage(name) {
      this.selectedLanguage = name;
      this.page = 1;
      await this.fetchBooks();
    },
    async fetchBooks() {
      this.loading = true;
      try {
        const start = (this.page - 1) * this.page_size;
        const rsp = await this.$backend(`/language/${encodeURIComponent(this.selectedLanguage)}?start=${start}&size=${this.page_size}`);
        if (rsp.err === 'ok') {
          this.books = rsp.books || [];
          this.total_books = rsp.total || 0;
          this.page_cnt = Math.max(1, Math.ceil(this.total_books / this.page_size));
        }
      } catch (e) {
        console.error(e);
      } finally {
        this.loading = false;
      }
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
.meta-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 16px;
}
.meta-tag {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
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
