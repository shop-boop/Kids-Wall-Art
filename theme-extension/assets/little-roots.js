/**
 * Little Roots PDP personalization.
 *
 * Mirrors shared/script_payload.py's _script_payload shape (spec Section 0)
 * by hand in JS since the theme runs outside the Python services — keep in
 * sync manually if the schema changes.
 *
 * Add-to-cart is gated on:
 *   1. a candidate selected from /transliterate results,
 *   2. a /render preview returned with render_id + render_hash,
 *   3. the customer explicitly checking "approve" on that exact preview.
 * Selecting a different candidate or retyping the name invalidates any
 * prior approval (spec Section 0: server must never trust a stale render).
 */
(function () {
  "use strict";

  function debounce(fn, ms) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  function initBlock(root) {
    const renderEndpoint = root.dataset.renderEndpoint;
    if (!renderEndpoint) {
      console.warn("[little-roots] render_endpoint block setting is unset — UPDATE ME in theme editor");
    }

    const nameInput = root.querySelector(".lr-name-input");
    const scriptSelect = root.querySelector(".lr-script-select");
    const candidatesEl = root.querySelector(".lr-candidates");
    const previewEl = root.querySelector(".lr-preview");
    const previewImg = root.querySelector(".lr-preview-img");
    const approveCheckbox = root.querySelector(".lr-approve-checkbox");
    const errorEl = root.querySelector(".lr-error");

    // Find the existing product form + its variant id input (spec 2.3) —
    // do not introduce a second variant selector.
    const productForm = root.closest("section")?.querySelector('form[action*="/cart/add"]')
      || document.querySelector('form[action*="/cart/add"]');

    let approvedRender = null; // { selected_native, render_id, render_hash, script, input_en }

    function showError(message) {
      errorEl.textContent = message;
      errorEl.hidden = !message;
    }

    function invalidateApproval() {
      approvedRender = null;
      previewEl.hidden = true;
      approveCheckbox.checked = false;
    }

    const fetchCandidates = debounce(async function () {
      invalidateApproval();
      const text = nameInput.value.trim();
      const lang = scriptSelect.value;
      candidatesEl.innerHTML = "";
      showError("");

      if (!text) return;

      try {
        const resp = await fetch(`${renderEndpoint}/transliterate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, lang, topk: 5 }),
        });
        if (!resp.ok) throw new Error(`transliterate failed: ${resp.status}`);
        const data = await resp.json();
        renderCandidates(data.candidates || [], text, lang);
      } catch (err) {
        console.error("[little-roots]", err);
        showError("Could not load spelling suggestions. Please try again.");
      }
    }, 350);

    function renderCandidates(candidates, inputEn, lang) {
      candidatesEl.innerHTML = "";
      if (candidates.length === 0) {
        showError("No suggestions found — double-check the spelling.");
        return;
      }
      candidates.forEach((native) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "lr-candidate-btn";
        btn.textContent = native;
        btn.setAttribute("role", "option");
        btn.addEventListener("click", () => selectCandidate(native, inputEn, lang));
        candidatesEl.appendChild(btn);
      });
    }

    async function selectCandidate(native, inputEn, lang) {
      invalidateApproval();
      candidatesEl.querySelectorAll(".lr-candidate-btn").forEach((b) => {
        b.classList.toggle("selected", b.textContent === native);
      });

      try {
        const resp = await fetch(`${renderEndpoint}/render`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            selected_native: native,
            script: lang,
            input_en: inputEn,
            // UPDATE ME: pull real canvas dimensions from the Printify
            // blueprint placeholder for the selected variant (spec 3.2)
            // instead of this placeholder size.
            canvas_width: 1200,
            canvas_height: 1200,
          }),
        });
        if (!resp.ok) throw new Error(`render failed: ${resp.status}`);
        const data = await resp.json();

        previewImg.src = data.url; // UPDATE ME: confirm this is a publicly fetchable preview URL, not a gs:// / r2:// URI
        previewEl.hidden = false;
        approvedRender = {
          selected_native: native,
          input_en: inputEn,
          script: lang,
          render_id: data.render_id,
          render_hash: data.render_hash,
        };
      } catch (err) {
        console.error("[little-roots]", err);
        showError("Could not generate preview. Please try again.");
      }
    }

    nameInput.addEventListener("input", fetchCandidates);
    scriptSelect.addEventListener("change", fetchCandidates);
    approveCheckbox.addEventListener("change", () => {
      if (!approveCheckbox.checked) approvedRender = null;
    });

    if (!productForm) {
      console.warn("[little-roots] no product form found — cannot wire add-to-cart gate");
      return;
    }

    productForm.addEventListener("submit", function (event) {
      if (!nameInput.value.trim()) return; // personalization not in use for this order

      if (!approvedRender || !approveCheckbox.checked) {
        event.preventDefault();
        showError("Please approve the preview before adding to cart.");
        return;
      }

      const variantInput = productForm.querySelector('input[name="id"]');
      if (!variantInput) {
        event.preventDefault();
        showError("Could not determine selected variant.");
        return;
      }

      event.preventDefault();
      addToCartWithPersonalization(variantInput.value, approvedRender);
    });

    async function addToCartWithPersonalization(variantId, render) {
      const scriptPayload = JSON.stringify({
        input_en: render.input_en,
        script: render.script,
        selected_native: render.selected_native,
        render_id: render.render_id,
        render_hash: render.render_hash,
      });

      try {
        const resp = await fetch("/cart/add.js", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: variantId,
            quantity: 1,
            properties: {
              "Name in script": render.selected_native,
              _script_payload: scriptPayload,
            },
          }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.description || `cart add failed: ${resp.status}`);
        }
        window.location.href = "/cart"; // UPDATE ME: replace with the theme's actual cart-drawer/redirect convention
      } catch (err) {
        console.error("[little-roots]", err);
        showError("Could not add to cart. Please try again.");
      }
    }
  }

  document.querySelectorAll(".little-roots-personalization").forEach(initBlock);
})();
