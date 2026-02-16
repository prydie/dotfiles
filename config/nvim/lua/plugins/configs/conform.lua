return {
  formatters_by_ft = {
    lua = { "stylua" },
    javascript = { "prettier" },
    javascriptreact = { "prettier" },
    typescript = { "prettier" },
    typescriptreact = { "prettier" },
    json = { "prettier" },
    yaml = { "prettier" },
    markdown = { "prettier" },
    python = { "isort", "black" },
    sh = { "shfmt" },
    go = { "goimports", "gofmt" },
    terraform = { "terraform_fmt" },
    hcl = { "terraform_fmt" },
    tfvars = { "terraform_fmt" },
    dockerfile = { "dockerfmt" },
  },
}
