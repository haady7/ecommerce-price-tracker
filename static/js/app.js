const form = document.getElementById("product-form");
const tbody = document.getElementById("products-body");
const message = document.getElementById("form-message");
const submitButton = document.getElementById("submit-btn");

function showMessage(text, type) {
  message.textContent = text;
  message.className = `message ${type}`;
}

function money(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);
}

async function loadProducts() {
  tbody.innerHTML = '<tr><td colspan="5" class="empty">Loading products…</td></tr>';
  try {
    const response = await fetch("/api/products");
    if (!response.ok) throw new Error("Could not load products.");
    const products = await response.json();
    if (!products.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">No products tracked yet. Add your first product above.</td></tr>';
      return;
    }
    tbody.replaceChildren();
    products.forEach(product => {
      const tr = document.createElement("tr");
      const nameCell = document.createElement("td");
      const link = document.createElement("a");
      link.href = product.product_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = product.product_name;
      nameCell.append(link);
      const current = document.createElement("td");
      current.className = "price";
      current.textContent = money(product.current_price);
      const target = document.createElement("td");
      target.className = "target";
      target.textContent = money(product.target_price);
      const checked = document.createElement("td");
      checked.textContent = product.last_checked_at || "Not checked";
      const action = document.createElement("td");
      const remove = document.createElement("button");
      remove.className = "delete";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => deleteProduct(product.id));
      action.append(remove);
      [nameCell, current, target, checked, action].forEach(cell => tr.append(cell));
      tbody.append(tr);
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">Unable to load products. Check that the server and database are running.</td></tr>';
  }
}

async function deleteProduct(id) {
  if (!window.confirm("Delete this product and all its price history?")) return;
  try {
    const response = await fetch(`/api/products/${id}`, { method: "DELETE" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Delete failed.");
    await loadProducts();
  } catch (error) {
    window.alert(error.message);
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  submitButton.disabled = true;
  showMessage("Fetching product details…", "");
  const payload = {
    url: document.getElementById("url").value.trim(),
    target_price: document.getElementById("target_price").value,
    email: document.getElementById("email").value.trim()
  };
  try {
    const response = await fetch("/api/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not add product.");
    showMessage(`Added ${result.product.product_name} at ${money(result.product.current_price)}.`, "success");
    form.reset();
    await loadProducts();
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    submitButton.disabled = false;
  }
});

document.getElementById("refresh-btn").addEventListener("click", loadProducts);
loadProducts();
