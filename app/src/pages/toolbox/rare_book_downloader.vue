<template>
  <div class="rbd-page" :class="darkMode ? 'rbd-dark' : 'rbd-light'">
    <!-- Close button -->
    <button class="rbd-close" @click="$router.go(-1)" :title="$t('rareBookDownloader.close')">
      <span>✕</span>
    </button>

    <div class="rbd-center">
      <!-- Title -->
      <div class="rbd-title-wrap">
        <span class="rbd-icon">📖</span>
        <h1 class="rbd-title">{{ $t('rareBookDownloader.title') }}</h1>
      </div>

      <!-- Search bar -->
      <div class="rbd-search-bar">
        <input
          v-model="url"
          class="rbd-input"
          type="url"
          :placeholder="$t('rareBookDownloader.placeholder')"
          @keyup.enter="download"
          :disabled="loading"
        />
        <button
          class="rbd-btn-download"
          :class="{ 'rbd-btn-loading': loading }"
          @click="download"
          :disabled="loading"
        >
          <span v-if="loading" class="rbd-spinner" />
          <span v-else>{{ $t('rareBookDownloader.downloadBtn') }}</span>
        </button>
      </div>

      <!-- Result message -->
      <transition name="rbd-fade">
        <div v-if="resultMsg" class="rbd-result" :class="resultClass">
          {{ resultMsg }}
        </div>
      </transition>

      <!-- Description -->
      <p class="rbd-desc">
        {{ $t('rareBookDownloader.descPre') }}
        <a
          href="https://lbezone.hkust.edu.hk/rse/?s=*&sort=pubyear&order=asc&scopename=thread-bound-books"
          target="_blank"
          rel="noopener noreferrer"
          class="rbd-link"
        >{{ $t('rareBookDownloader.descLibrary') }}</a>{{ $t('rareBookDownloader.descPost') }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  data: () => ({
    url: '',
    loading: false,
    resultMsg: '',
    resultClass: '',
  }),
  computed: {
    darkMode() {
      return this.$store.state.dark;
    },
  },
  created() {
    this.$store.commit('navbar', false);
  },
  beforeDestroy() {
    this.$store.commit('navbar', true);
  },
  methods: {
    async download() {
      this.resultMsg = '';
      const trimmed = this.url.trim();
      if (!trimmed) {
        this.resultMsg = this.$t('rareBookDownloader.errorEmptyUrl');
        this.resultClass = 'rbd-result-error';
        return;
      }
      this.loading = true;
      try {
        const rsp = await this.$backend('/admin/toolbox/rare_book_downloader', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: trimmed }),
        });
        this.resultMsg = rsp.msg || (rsp.err === 'ok' ? this.$t('rareBookDownloader.success') : rsp.err);
        this.resultClass = rsp.err === 'ok' ? 'rbd-result-ok' : 'rbd-result-error';
      } catch (e) {
        this.resultMsg = String(e);
        this.resultClass = 'rbd-result-error';
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style scoped>
/* ── Base layout ── */
.rbd-page {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  transition: background 0.3s;
}

.rbd-light {
  background: #f5f7fa;
  color: #1a1a2e;
}

.rbd-dark {
  background: #12141a;
  color: #e8eaf0;
}

/* ── Close button ── */
.rbd-close {
  position: absolute;
  top: 20px;
  right: 24px;
  background: #d32f2f;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: 0.02em;
  box-shadow: 0 2px 8px rgba(211, 47, 47, 0.35);
  transition: opacity 0.2s, transform 0.15s;
}
.rbd-close:hover {
  opacity: 0.85;
  transform: scale(1.04);
}

/* ── Center block ── */
.rbd-center {
  width: 100%;
  max-width: 640px;
  padding: 0 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

/* ── Title ── */
.rbd-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rbd-icon {
  font-size: 36px;
  line-height: 1;
}

.rbd-title {
  margin: 0;
  font-size: clamp(1.5rem, 4vw, 2.2rem);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.rbd-light .rbd-title {
  color: #003153;
}

.rbd-dark .rbd-title {
  color: #90caf9;
}

/* ── Search bar ── */
.rbd-search-bar {
  display: flex;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 49, 83, 0.15);
}

.rbd-dark .rbd-search-bar {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
}

.rbd-input {
  flex: 1;
  min-width: 0;
  padding: 14px 18px;
  font-size: 15px;
  border: none;
  outline: none;
  transition: background 0.2s;
}

.rbd-light .rbd-input {
  background: #fff;
  color: #1a1a2e;
}

.rbd-dark .rbd-input {
  background: #1e2130;
  color: #e8eaf0;
}

.rbd-input::placeholder {
  color: #a0aab4;
}

.rbd-input:disabled {
  opacity: 0.6;
}

.rbd-btn-download {
  background: #003153;
  color: #fff;
  border: none;
  padding: 0 28px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.03em;
  transition: background 0.2s, opacity 0.2s;
  min-width: 96px;
  justify-content: center;
}

.rbd-btn-download:hover:not(:disabled) {
  background: #004a7c;
}

.rbd-btn-download:disabled,
.rbd-btn-loading {
  opacity: 0.7;
  cursor: not-allowed;
}

/* ── Spinner ── */
.rbd-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: rbd-spin 0.7s linear infinite;
}

@keyframes rbd-spin {
  to { transform: rotate(360deg); }
}

/* ── Result message ── */
.rbd-result {
  width: 100%;
  padding: 12px 18px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
}

.rbd-result-ok {
  background: rgba(46, 125, 50, 0.12);
  color: #2e7d32;
  border: 1px solid rgba(46, 125, 50, 0.3);
}

.rbd-dark .rbd-result-ok {
  background: rgba(102, 187, 106, 0.15);
  color: #a5d6a7;
  border-color: rgba(102, 187, 106, 0.3);
}

.rbd-result-error {
  background: rgba(211, 47, 47, 0.1);
  color: #c62828;
  border: 1px solid rgba(211, 47, 47, 0.25);
}

.rbd-dark .rbd-result-error {
  background: rgba(239, 83, 80, 0.15);
  color: #ef9a9a;
  border-color: rgba(239, 83, 80, 0.3);
}

/* ── Description ── */
.rbd-desc {
  margin: 0;
  width: 100%;
  font-size: 13px;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-align: left;
}

.rbd-light .rbd-desc {
  color: #606880;
}

.rbd-dark .rbd-desc {
  color: #8892a4;
}

.rbd-link {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.rbd-light .rbd-link {
  color: #003153;
}

.rbd-dark .rbd-link {
  color: #90caf9;
}

.rbd-link:hover {
  opacity: 0.75;
}

/* ── Transition ── */
.rbd-fade-enter-active,
.rbd-fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.rbd-fade-enter,
.rbd-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
