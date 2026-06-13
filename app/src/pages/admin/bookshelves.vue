<template>
  <v-card>
    <v-card-title>
      <v-icon left>mdi-bookshelf</v-icon>
      {{ $t('bookshelves.pageTitle') }}
      <v-spacer></v-spacer>
      <v-text-field
        v-model="newName"
        :label="$t('bookshelves.addLabel')"
        :placeholder="$t('bookshelves.addPlaceholder')"
        outlined
        dense
        hide-details
        style="max-width: 300px;"
        @keyup.enter="addBookshelf"
        class="mr-2"
      >
        <template v-slot:append-outer>
          <v-btn icon color="primary" @click="addBookshelf" :loading="adding" :disabled="!newName.trim()">
            <v-icon>mdi-plus</v-icon>
          </v-btn>
        </template>
      </v-text-field>
    </v-card-title>

    <v-card-text>
      <p class="text-body-2 grey--text mb-4">{{ $t('bookshelves.description') }}</p>
      <v-data-table
        :headers="headers"
        :items="items"
        :loading="loading"
        :items-per-page="100"
        hide-default-footer
        class="elevation-1"
      >
        <template v-slot:item.index="{ item }">
          {{ items.indexOf(item) + 1 }}
        </template>
        <template v-slot:item.actions="{ item }">
          <v-btn small color="primary" text @click="editBookshelf(item)">
            <v-icon small left>mdi-pencil</v-icon>
            {{ $t('bookshelves.edit') }}
          </v-btn>
          <v-btn small color="error" text @click="deleteBookshelf(item)">
            <v-icon small left>mdi-delete</v-icon>
            {{ $t('bookshelves.delete') }}
          </v-btn>
        </template>
        <template v-slot:no-data>
          <div class="py-4 text-center grey--text">
            {{ $t('bookshelves.empty') }}
          </div>
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Edit dialog -->
    <v-dialog v-model="showEditDialog" max-width="400px">
      <v-card>
        <v-card-title>{{ $t('bookshelves.editTitle') }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="editingName"
            :label="$t('bookshelves.editLabel')"
            outlined
            dense
            autofocus
            @keyup.enter="confirmEdit"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showEditDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="primary" @click="confirmEdit" :loading="editing" :disabled="!editingName.trim() || editingName.trim() === editingOriginalName">{{ $t('common.save') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete confirm dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400px">
      <v-card>
        <v-card-title>{{ $t('bookshelves.deleteConfirmTitle') }}</v-card-title>
        <v-card-text>
          {{ $t('bookshelves.deleteConfirmMessage', { name: deletingName }) }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="showDeleteDialog = false">{{ $t('common.cancel') }}</v-btn>
          <v-btn color="error" @click="confirmDelete" :loading="deleting">{{ $t('common.delete') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script>
export default {
  data() {
    return {
      items: [],
      loading: false,
      adding: false,
      newName: '',
      showDeleteDialog: false,
      deletingName: '',
      deleting: false,
      showEditDialog: false,
      editingOriginalName: '',
      editingName: '',
      editing: false,
    };
  },
  head() {
    return { title: this.$t('bookshelves.pageTitle') };
  },
  computed: {
    headers() {
      return [
        { text: '#', value: 'index', sortable: false, width: '80px' },
        { text: this.$t('bookshelves.nameColumn'), value: 'name', sortable: true },
        { text: this.$t('bookshelves.actions'), value: 'actions', sortable: false, width: '200px' },
      ];
    },
  },
  mounted() {
    this.fetchItems();
  },
  methods: {
    fetchItems() {
      this.loading = true;
      this.$backend('/admin/bookshelves')
        .then(rsp => {
          if (rsp.err === 'ok') {
            this.items = (rsp.bookshelves || []).map(name => ({ name }));
          } else {
            this.$alert('error', rsp.msg);
          }
        })
        .finally(() => {
          this.loading = false;
        });
    },
    addBookshelf() {
      const name = this.newName.trim();
      if (!name) return;
      this.adding = true;
      this.$backend('/admin/bookshelves', {
        method: 'POST',
        body: JSON.stringify({ name }),
      }).then(rsp => {
        if (rsp.err === 'ok') {
          this.items = (rsp.bookshelves || []).map(n => ({ name: n }));
          this.newName = '';
          this.$alert('success', this.$t('bookshelves.addSuccess'));
        } else {
          this.$alert('error', rsp.msg);
        }
      }).finally(() => {
        this.adding = false;
      });
    },
    deleteBookshelf(item) {
      this.deletingName = item.name;
      this.showDeleteDialog = true;
    },
    editBookshelf(item) {
      this.editingOriginalName = item.name;
      this.editingName = item.name;
      this.showEditDialog = true;
    },
    confirmEdit() {
      const newName = this.editingName.trim();
      if (!newName || newName === this.editingOriginalName) return;
      this.editing = true;
      this.$backend('/admin/bookshelves', {
        method: 'PUT',
        body: JSON.stringify({ old_name: this.editingOriginalName, new_name: newName }),
      }).then(rsp => {
        if (rsp.err === 'ok') {
          this.items = (rsp.bookshelves || []).map(n => ({ name: n }));
          this.showEditDialog = false;
          this.$alert('success', this.$t('bookshelves.editSuccess'));
        } else {
          this.$alert('error', rsp.msg);
        }
      }).finally(() => {
        this.editing = false;
      });
    },
    confirmDelete() {
      this.deleting = true;
      this.$backend('/admin/bookshelves', {
        method: 'DELETE',
        body: JSON.stringify({ name: this.deletingName }),
      }).then(rsp => {
        if (rsp.err === 'ok') {
          this.items = (rsp.bookshelves || []).map(n => ({ name: n }));
          this.showDeleteDialog = false;
          this.$alert('success', this.$t('bookshelves.deleteSuccess'));
        } else {
          this.$alert('error', rsp.msg);
        }
      }).finally(() => {
        this.deleting = false;
      });
    },
  },
};
</script>

<style scoped>
</style>
