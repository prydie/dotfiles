return {
  { "nvim-lua/plenary.nvim", lazy = true },
  { "nvim-tree/nvim-web-devicons", opts = {} },
  { "EdenEast/nightfox.nvim", lazy = false, priority = 1000 },

  -- UI
  { "echasnovski/mini.statusline", opts = {} }, -- vim-airline replacement
  { "akinsho/bufferline.nvim", opts = require "plugins.configs.bufferline" },
  {
    "folke/which-key.nvim",
    event = "VeryLazy",
    config = function()
      local wk = require "which-key"
      wk.setup {}
      wk.add {
        { "<leader>a", group = "Aerial" },
        { "<leader>d", group = "Debug" },
        { "<leader>e", group = "ESP32" },
        { "<leader>f", group = "Find/Format" },
        { "<leader>g", group = "Git" },
        { "<leader>k", group = "Kubernetes" },
        { "<leader>s", group = "Search" },
        { "<leader>t", group = "Test/Tofu" },
        { "<leader>x", group = "Trouble/Todo" },
      }
    end,
    keys = {
      {
        "<leader>?",
        function()
          require("which-key").show { global = false }
        end,
        desc = "Buffer local keymaps",
      },
    },
  },
  {
    "folke/snacks.nvim",
    priority = 1000,
    lazy = false,
    opts = {
      bigfile = { enabled = true },
      dashboard = { enabled = true },
      explorer = { enabled = true },
      indent = { enabled = true },
      input = { enabled = true },
      picker = { enabled = true },
      notifier = { enabled = true },
      quickfile = { enabled = true },
      scope = { enabled = true },
      scroll = { enabled = true },
      statuscolumn = { enabled = true },
      words = { enabled = true },
    },
    keys = {
      { "<leader>gB", function() Snacks.gitbrowse() end, desc = "Git Browse", mode = { "n", "v" } },
    },
  },

  -- Navigation / finders
  {
    "nvim-neo-tree/neo-tree.nvim",
    branch = "v3.x",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "MunifTanjim/nui.nvim",
      "nvim-tree/nvim-web-devicons",
    },
    lazy = false,
    opts = {
      filesystem = {
        filtered_items = {
          hide_by_name = { "__pycache__" },
        },
      },
    },
  }, -- NERDTree replacement
  {
    "ibhagwan/fzf-lua",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    opts = {
      "border-fused",
      fzf_colors = true,
      winopts = {
        height = 0.85,
        width = 0.9,
        preview = {
          layout = "horizontal",
          horizontal = "right:50%",
        },
      },
      files = {
        fd_opts = [[--color=never --type f --hidden --follow --exclude .git]],
      },
      grep = {
        rg_opts = "--column --line-number --no-heading --color=always --smart-case --max-columns=512 -e",
      },
    },
  }, -- fzf + ack.vim replacement
  {
    "MagicDuck/grug-far.nvim",
    opts = { headerMaxWidth = 80 },
    cmd = "GrugFar",
    keys = {
      {
        "<leader>sr",
        function()
          local grug = require "grug-far"
          local ext = vim.bo.buftype == "" and vim.fn.expand "%:e"
          grug.open {
            transient = true,
            prefills = {
              filesFilter = ext and ext ~= "" and "*." .. ext or nil,
            },
          }
        end,
        mode = { "n", "v" },
        desc = "Search and replace",
      },
    },
  },
  {
    "folke/trouble.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("trouble").setup {
        auto_close = false,
        auto_open = false,
        focus = true,
        warn_no_results = false,
      }
    end,
    keys = {
      { "<leader>xx", "<cmd>Trouble diagnostics toggle<CR>", desc = "Diagnostics (Trouble)" },
      { "<leader>xq", "<cmd>Trouble qflist toggle<CR>", desc = "Quickfix (Trouble)" },
      { "<leader>xl", "<cmd>Trouble loclist toggle<CR>", desc = "Loclist (Trouble)" },
      { "<leader>xr", "<cmd>Trouble lsp_references toggle<CR>", desc = "LSP References (Trouble)" },
    },
  },
  {
    "folke/todo-comments.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    event = { "BufReadPost", "BufNewFile" },
    config = function()
      require("todo-comments").setup {
        signs = true,
        highlight = {
          multiline = true,
        },
        search = {
          command = "rg",
          args = {
            "--color=never",
            "--no-heading",
            "--with-filename",
            "--line-number",
            "--column",
          },
        },
      }
    end,
    keys = {
      { "]t", function() require("todo-comments").jump_next() end, desc = "Next TODO" },
      { "[t", function() require("todo-comments").jump_prev() end, desc = "Prev TODO" },
      { "<leader>xt", "<cmd>TodoTrouble<CR>", desc = "TODOs (Trouble)" },
      { "<leader>xT", "<cmd>TodoQuickFix<CR>", desc = "TODOs (Quickfix)" },
    },
  },
  { "stevearc/aerial.nvim", opts = {} }, -- tagbar replacement

  -- Editing UX
  { "numToStr/Comment.nvim", opts = {} }, -- nerdcommenter replacement
  { "kylechui/nvim-surround", version = "*", opts = {} }, -- vim-surround replacement
  {
    "nvimdev/indentmini.nvim",
    event = { "BufReadPre", "BufNewFile" },
    opts = {},
  },

  -- Syntax / language
  {
    "nvim-treesitter/nvim-treesitter",
    build = function()
      pcall(vim.cmd, "TSUpdate")
    end,
    config = function()
      require "plugins.configs.treesitter"
    end,
  }, -- vim-polyglot replacement
  {
    "saghen/blink.cmp",
    version = "1.*",
    event = "InsertEnter",
    dependencies = {
      "rafamadriz/friendly-snippets",
      {
        "L3MON4D3/LuaSnip",
        config = function()
          require("luasnip.loaders.from_vscode").lazy_load()
        end,
      },
      { "windwp/nvim-autopairs", opts = {} },
    },
    opts = function()
      return require "plugins.configs.blink"
    end,
  }, -- coc/deoplete replacement
  {
    "williamboman/mason.nvim",
    build = function()
      pcall(vim.cmd, "MasonUpdate")
    end,
    cmd = { "Mason", "MasonInstall" },
    opts = {},
  },
  {
    "neovim/nvim-lspconfig",
    config = function()
      require "plugins.configs.lspconfig"
    end,
  },
  {
    "stevearc/conform.nvim",
    opts = require "plugins.configs.conform",
  }, -- formatter replacement for ALE fixers
  {
    "mfussenegger/nvim-lint",
    config = function()
      local lint = require "lint"
      lint.linters_by_ft = {
        python = { "ruff" },
        go = { "golangcilint" },
        javascript = { "eslint_d" },
        javascriptreact = { "eslint_d" },
        typescript = { "eslint_d" },
        typescriptreact = { "eslint_d" },
        sh = { "shellcheck" },
        lua = { "selene" },
        terraform = { "tflint" },
        dockerfile = { "hadolint" },
      }

      vim.api.nvim_create_autocmd({ "BufWritePost", "InsertLeave" }, {
        callback = function()
          lint.try_lint()
        end,
      })
    end,
  }, -- ALE linter replacement
  {
    "mfussenegger/nvim-dap",
    dependencies = {
      "rcarriga/nvim-dap-ui",
      "theHamsta/nvim-dap-virtual-text",
      "mfussenegger/nvim-dap-python",
      "leoluz/nvim-dap-go",
    },
    config = function()
      require "plugins.configs.dap"
    end,
  },

  -- Git
  { "lewis6991/gitsigns.nvim", opts = {} }, -- gitgutter replacement
  {
    "NeogitOrg/neogit",
    dependencies = { "nvim-lua/plenary.nvim" },
    opts = {},
    keys = {
      { "<leader>gg", "<cmd>Neogit<CR>", desc = "Open Neogit" },
    },
  }, -- fugitive replacement

  -- Notes / tests
  {
    "vimwiki/vimwiki",
    init = function()
      vim.g.vimwiki_list = {
        {
          path = "~/vimwiki/",
          syntax = "markdown",
          ext = ".md",
        },
      }
    end,
  },
  {
    "nvim-neotest/neotest",
    dependencies = {
      "nvim-neotest/nvim-nio",
      "nvim-lua/plenary.nvim",
      "antoinemadec/FixCursorHold.nvim",
      "nvim-treesitter/nvim-treesitter",
      "nvim-neotest/neotest-python",
      "nvim-neotest/neotest-go",
    },
    config = function()
      require("neotest").setup {
        adapters = {
          require("neotest-python") {},
          require("neotest-go") {},
        },
      }
    end,
    keys = {
      { "<leader>t", "", desc = "+test" },
      {
        "<leader>tt",
        function()
          local project_env = require "project_env"
          if vim.bo.filetype == "python" and project_env.detect_django_runtime() then
            project_env.run_django_test_current_file()
            return
          end
          require("neotest").run.run(vim.fn.expand "%")
        end,
        desc = "Run file",
      },
      {
        "<leader>tT",
        function()
          require("neotest").run.run(vim.uv.cwd())
        end,
        desc = "Run all tests",
      },
      {
        "<leader>tr",
        function()
          local project_env = require "project_env"
          if vim.bo.filetype == "python" and project_env.detect_django_runtime() then
            project_env.run_django_test_nearest()
            return
          end
          require("neotest").run.run()
        end,
        desc = "Run nearest test",
      },
      {
        "<leader>tl",
        function()
          local project_env = require "project_env"
          if vim.bo.filetype == "python" and project_env.detect_django_runtime() then
            project_env.run_django_test_last()
            return
          end
          require("neotest").run.run_last()
        end,
        desc = "Run last test",
      },
      {
        "<leader>ts",
        function()
          require("neotest").summary.toggle()
        end,
        desc = "Toggle summary",
      },
      {
        "<leader>to",
        function()
          require("neotest").output.open { enter = true, auto_close = true }
        end,
        desc = "Show output",
      },
      {
        "<leader>tO",
        function()
          require("neotest").output_panel.toggle()
        end,
        desc = "Toggle output panel",
      },
      {
        "<leader>tS",
        function()
          require("neotest").run.stop()
        end,
        desc = "Stop test",
      },
      {
        "<leader>tw",
        function()
          require("neotest").watch.toggle(vim.fn.expand "%")
        end,
        desc = "Toggle watch",
      },
    },
  },
  {
    "vim-test/vim-test",
    config = function()
      vim.g["test#strategy"] = "neovim"
      vim.g["test#neovim#term_position"] = "botright 15split"
      vim.g["test#python#runner"] = "pytest"
    end,
  },
}
