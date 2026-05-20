<template>
  <div class="wap-page">
    <wap-header />
    <main class="wap-main">
      <h2 class="wap-page-title">{{ $t('listBook.wantsBooks') }}</h2>
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
      books: [],
      page: 1,
      page_size: 60,
      total: 0,
      page_cnt: 0
    };
  },
  async created() {
    await this.fetchBooks();
  },
  methods: {
    async fetchBooks() {
      const start = (this.page - 1) * this.page_size;
      try {
        const rsp = await this.$backend(`/wants?start=${start}&size=${this.page_size}`);
        if (rsp.err === 'ok') {
          this.books = rsp.books || [];
          this.total = rsp.total;
          this.page_cnt = Math.max(1, Math.ceil(this.total / this.page_size));
        }
      } catch (e) {
        console.error(e);
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
