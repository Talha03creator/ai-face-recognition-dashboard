/**
 * API.js — clean wrapper around all backend endpoints.
 * Every function returns a parsed JSON object or { error: string }.
 */
const API = (() => {
    const BASE = '/api';

    async function req(url, opts = {}) {
        try {
            const res = await fetch(BASE + url, opts);
            if (!res.ok) {
                return { error: `HTTP ${res.status}: ${res.statusText}` };
            }
            return await res.json();
        } catch (err) {
            return { error: err.message || 'Network error' };
        }
    }

    return {
        // Detection
        uploadDetect(file) {
            const fd = new FormData();
            fd.append('file', file);
            return req('/detect/upload', { method: 'POST', body: fd });
        },

        matchFaces(target, group) {
            const fd = new FormData();
            fd.append('target', target);
            fd.append('group', group);
            return req('/detect/match', { method: 'POST', body: fd });
        },

        fetchProgress(taskId) {
            return req(`/detect/progress/${taskId}`);
        },

        fetchResult(taskId) {
            return req(`/detect/result/${taskId}`);
        },

        // Users
        fetchUsers()          { return req('/users/');          },
        registerUser(name, file) {
            const fd = new FormData();
            fd.append('name', name);
            fd.append('file', file);
            return req('/users/register', { method: 'POST', body: fd });
        },
        deleteUser(name)      { return req(`/users/${name}`, { method: 'DELETE' }); },

        // Logs
        fetchLogs()           { return req('/logs/');           },
    };
})();
