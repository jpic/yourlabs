$(document).bind('yourlabs.autocomplete.optionSelected', function(e, autocomplete, option) {
    link = $(option).find('a:first');
    if (link.length && link.attr('href') != undefined) {
        window.location.href = link.attr('href');
        return false;
    } else {
        alert('sorry, i dunno what to do with your selection!!');
    }
});

(function($) {
    function Autocomplete(el, options) {
        this.el = el;
        this.el.attr('autocomplete', 'off');
        this.value = '';
        this.xhr = false;
        this.options = {
            url: false,
            timeout: 100,
            id: false,
            minCharacters: 2,
            defaultValue: 'type your search here',
        };
        this.setOptions(options);
        this.initialize();
    }

    $.fn.yourlabs_autocomplete = function(options) {
        var id;
        options = options ? options : {};
        id = options.id || this.attr('id');

        if (!(id && this)) {
            alert('failure: the element needs an id attribute, or an id option must be passed');
            return false;
        }
        
        if ($.fn.yourlabs_autocomplete.registry == undefined) {
            $.fn.yourlabs_autocomplete.registry = {};
        }
        
        if ($.fn.yourlabs_autocomplete.registry[id] == undefined) {
            $.fn.yourlabs_autocomplete.registry[id] = new Autocomplete(this, options);
        }

        return $.fn.yourlabs_autocomplete.registry[id];
    };

    Autocomplete.prototype = {
        initialize: function() {
            var autocomplete;
            autocomplete = this;

            this.el.val(this.options.defaultValue);
            this.el.live('focus', function() {
                if ($(this).val() == autocomplete.options.defaultValue) {
                    $(this).val('');
                }
            });
            this.el.live('blur', function() {
                if ($(this).val() == '') {
                    $(this).val(autocomplete.options.defaultValue);
                }
            });

            $('.yourlabs_autocomplete.inner_container.id_'+this.options.id+' .option').live({
                mouseenter: function(e) {
                    $(this).addClass('active');
                },
                mouseleave: function(e) {
                    $(this).removeClass('active');
                },
                click: function(e) {
                    var link, text;
                    if (e.target != this) {
                        return false;
                    }
                    e.preventDefault();
                    e.stopPropagation();
                    $(document).trigger('yourlabs.autocomplete.optionSelected', [autocomplete, this]);
                },
            });

            function refresh() {
                autocomplete.refresh();
                window.setTimeout(refresh, autocomplete.options.timeout);
            }
            window.setTimeout(refresh, this.options.timeout);

            $('<div class="yourlabs_autocomplete outer_container id_'+this.options.id+'" style="position:absolute;z-index:9999;"><div class="yourlabs_autocomplete id_'+this.options.id+'"><div class="yourlabs_autocomplete inner_container  id_'+this.options.id+'" style="display:none;"></div></div></div>').appendTo('body');
            this.innerContainer = $('.yourlabs_autocomplete.inner_container.id_'+this.options.id);
            this.outerContainer = $('.yourlabs_autocomplete.outer_container.id_'+this.options.id);


        },
        fixPosition: function() {
            var offset = this.el.offset();
            this.outerContainer.css({ top: (offset.top + this.el.innerHeight()) + 'px', left: offset.left + 'px' });
        },
        refresh: function() {
            var newValue;
            newValue = this.el.val();
            if (newValue == this.options.defaultValue) {
                return false;
            }
            if (newValue.length < this.options.minCharacters) {
                return false;
            }
            if (newValue == this.value) {
                return false;
            }
            this.value = newValue;
            this.fetchAutocomplete();
        },
        fetchAutocomplete: function() {
            var autocomplete;

            if (this.xhr) {
                this.xhr.abort();
            }

            autocomplete = this;
            this.xhr = $.ajax(this.options.url, {
                'complete': function(jqXHR, textStatus) {
                    autocomplete.fixPosition();
                    autocomplete.innerContainer.html(jqXHR.responseText);
                    autocomplete.innerContainer.show();
                },
            });
        },
        setOptions: function(options){
            var o = this.options;
            $.extend(o, options);
        },
    }

}(jQuery));
