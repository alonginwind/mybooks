<template>
    <v-container fluid class="pa-4">
        <v-row class="mb-3" align="center">
            <v-col>
                <span class="text-h5 font-weight-bold">{{ $t('resources.pageTitle') }}</span>
                <div class="text-caption grey--text mt-1">{{ $t('resources.pageSubtitle') }}</div>
            </v-col>
        </v-row>

        <v-alert v-if="error" type="error" dense class="mb-4">{{ error }}</v-alert>

        <v-row v-if="loading" justify="center" class="py-10">
            <v-progress-circular indeterminate color="primary" size="48" />
        </v-row>

        <v-row v-else-if="resources.length === 0" justify="center" class="py-10">
            <v-col cols="auto" class="text-center grey--text">{{ $t('resources.noResources') }}</v-col>
        </v-row>

        <v-row v-else>
            <v-col
                v-for="(resource, idx) in resources"
                :key="idx"
                cols="12"
                md="4"
            >
                <resource-card
                    :icon="resource.icon"
                    :title="$te(resource.title) ? $t(resource.title) : resource.title"
                    :description="resource.description ? ($te(resource.description) ? $t(resource.description) : resource.description) : ''"
                    :link="resource.link"
                />
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
import ResourceCard from '~/components/ResourceCard.vue';

export default {
    components: { ResourceCard },
    data() {
        return {
            loading: true,
            error: '',
            resources: [],
        };
    },
    mounted() {
        this.$backend('/admin/resources').then(rsp => {
            this.loading = false;
            if (rsp.err === 'ok') {
                this.resources = rsp.resources || [];
            } else {
                this.error = rsp.msg || this.$t('resources.loadError');
            }
        }).catch(() => {
            this.loading = false;
            this.error = this.$t('resources.loadError');
        });
    },
};
</script>
