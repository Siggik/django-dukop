$(document).ready(function() {
    $('.formset-add-link').click(function() {
        $(this).parents(".formset--element").next().show('fast');
    });
    $('.formset-remove-link').click(function() {
        $(this).parents(".formset--element").hide('fast');
        $(this).parents(".formset--element").find("input[name=*DELETE]").prop('checked', true);
    });


    // Re-enable buttons, since on history.back() and such, the buttons will
    // appear already disabled, which is undesirable in case of a failure
    // during submission
    $('.event__form button[type=submit]').attr("disabled", false);

    $('.event__form').submit(function(){
        $('.event__form button[type=submit]').attr("disabled", true);
        $('.event__form button[type=submit]').text(gettext("Please wait..."));
    });

});


// https://stackoverflow.com/a/54574537/405682
var isSubmitting = false;

$(document).ready(function () {
    $('form').submit(function(){
        isSubmitting = true;
    });

    $('form').data('initial-state', $('form').serialize());

    $(window).on('beforeunload', function() {
        if (!isSubmitting && $('form').serialize() != $('form').data('initial-state')){
            return 'You have unsaved changes which will not be saved.';
        }
    });
});
