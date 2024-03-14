const yaml = require('js-yaml');
class SignalwireML {
    constructor(args) {
        this._content = {
            version: args.version || '1.0.0',
            sections: {},
            engine: args.engine || 'gcloud',
        }
        this._voice = args.voice || null;
        this._languages = [];
        this._pronounce = [];
        this._SWAIG = {
            includes: [],
            functions: [],
            native_functions: [],
            defaults: {},
        };
        this._params = {};
        this._prompt = {};
        this._post_prompt = {};
        this._hints = [];
    }

    add_aiapplication(section) {
        const app = "ai";
        const args = {};
        const dataFields = ["post_prompt", "voice", "engine", "post_prompt_url", "post_prompt_auth_user", "post_prompt_auth_password", "languages", "hints", "params", "prompt", "SWAIG", "pronounce"];

        for (const data of dataFields) {
            if (this["_" + data]) {
                args[data] = this["_" + data];
            }
        }

        this._content.sections[section] = this._content.sections[section] || [];
        this._content.sections[section].push({ [app]: args });
    }

    add_application(section, app, args) {
        this._content.sections[section] = this._content.sections[section] || [];
        this._content.sections[section].push({ [app]: args });
    }

    set_aipost_prompt_url(postprompt) {
        for (const [k, v] of Object.entries(postprompt)) {
            this["_" + k] = v;
        }
    }

    set_aiparams(params) {
        this._params = params;
    }

    add_aiparams(params) {
        const keys = ["end_of_speech_timeout", "attention_timeout", "outbound_attention_timeout", "background_file_loops", "background_file_volume", "digit_timeout", "energy_level"];

        for (const [k, v] of Object.entries(params)) {
            this._params[k] = keys.includes(k) ? parseInt(v) : v;
        }
    }

    set_aihints(...args) {
        this._hints = args;
    }

    add_aihints(...args) {
        const hints = args;
        const seen = new Set(this._hints);
        this._hints.push(...hints.filter(h => !seen.has(h)));
    }

    add_aiswaigdefaults(SWAIG) {
        Object.assign(this._SWAIG.defaults, SWAIG);
    }

    add_aiswaigfunction(SWAIG) {
        this._SWAIG.functions.push(SWAIG);
    }

    set_aipronounce(pronounce) {
        this._pronounce = pronounce;
    }

    add_aipronounce(pronounce) {
        this._pronounce.push(pronounce);
    }

    set_ailanguage(language) {
        this._languages = language;
    }

    add_ailanguage(language) {
        this._languages.push(language);
    }

    add_aiinclude(include) {
        this._SWAIG.includes.push(include);
    }

    add_ainativefunction(native) {
        this._SWAIG.native_functions.push(native);
    }

    set_aipost_prompt(postprompt) {
        const keys = ["confidence", "barge_confidence", "top_p", "temperature", "frequency_penalty", "presence_penalty"];

        for (const [k, v] of Object.entries(postprompt)) {
            this._post_prompt[k] = keys.includes(k) ? parseFloat(v) : v;
        }
    }

    set_aiprompt(prompt) {
        const keys = ["confidence", "barge_confidence", "top_p", "temperature", "frequency_penalty", "presence_penalty"];

        for (const [k, v] of Object.entries(prompt)) {
            this._prompt[k] = keys.includes(k) ? parseFloat(v) : v;
        }
    }

    swaig_response(response) {
        return response;
    }

    swaig_response_json(response) {
        return JSON.stringify(response, null, 4);
    }

    render() {
        return this._content;
    }

    render_json() {
        return JSON.stringify(this._content, null, 4);
    }

    render_yaml() {
        return yaml.dump(this._content);
    }

}
module.exports = SignalwireML;
