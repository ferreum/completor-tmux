if exists('g:loaded_completor_tmux_plugin')
  finish
endif

let g:loaded_completor_tmux_plugin = 1
let s:py = has('python3') ? 'py3' : 'py'


function! s:import_python() abort
  exe s:py 'import completor_tmux'
  exe s:py 'import completor, completers.common'
  exe s:py 'completor.get("common").hooks.append(completor_tmux.Tmux.filetype)'
endfunction


function! s:enable() abort
  augroup completor_tmux
    autocmd!
  augroup END
  call s:import_python()
endfunction


augroup completor_tmux
  autocmd!
  autocmd InsertEnter * call s:enable()
augroup END

" vim:set sw=2 ts=2 sts=0 et sta sr ft=vim fdm=marker:
