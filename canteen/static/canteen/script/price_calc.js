window.addEventListener("DOMContentLoaded", calculator);

function insertAfter(newNode, referenceNode) {
    referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

function calculator() {
    prepare();
    prepare_cashier();
}

var receipt = [];
var sum_indicator = [];
var subtotal = [];
var cashier;

function Course(price, amount) {
    this.price = price;
    this.amount = amount;
}

function prepare() {
    var table = document.getElementsByTagName("table");
    for (var i = 0; i < table.length; i++) {
        var menu = table[i];
        var course = menu.getElementsByClassName("course");

        var invoice = [];
        for (var j = 0; j < course.length; j++) {
            var price = parseFloat(course[j].children[3].textContent);

            var radio_buttons = course[j].children[4].getElementsByTagName("input");
            for (var k = 0; k < radio_buttons.length; k++) {
                if (radio_buttons[k].checked) {
                    var amount = parseInt(radio_buttons[k].value);
                }

                radio_buttons[k].addEventListener("change", modify_count);
            }

            invoice.push(new Course(price, amount));
        }

        receipt.push(invoice);

        var total_indicator = document.createElement("div");
        total_indicator.setAttribute("class", "sub total");
        var indicator_text = document.createTextNode("小计：");
        total_indicator.appendChild(indicator_text);

        var total_num = document.createElement("span");
        total_num.setAttribute("class", "sum_value");

        total_indicator.appendChild(total_num);

        sum_indicator.push(total_num);

        var total = sum(invoice);
        total_num.textContent = Math.round(total * 100) / 100; // https://stackoverflow.com/a/11832950
        subtotal.push(total);
        insertAfter(total_indicator, menu);
    }
}

function prepare_cashier() {
    var separator = document.getElementById("separator");
    var cashier_element = document.createElement("div");
    cashier_element.setAttribute("class", "total");
    var cashier_text = document.createTextNode("总计：");
    cashier_element.appendChild(cashier_text);

    var cashier_num = document.createElement("span");
    cashier_num.setAttribute("class", "sum_value");
    cashier_element.appendChild(cashier_num);

    cashier = cashier_num;
    insertAfter(cashier_element, separator);

    checkout();
}

function modify_count() {
    var location = this.name.split("-");
    var menu = location[0], course = location[1];
    receipt[menu][course].amount = parseInt(this.value);

    var total = sum(receipt[menu]);
    sum_indicator[menu].textContent = Math.round(total * 100) / 100; // https://stackoverflow.com/a/11832950
    subtotal[menu] = total;

    checkout();
}

function sum(current_menu) {
    var sum = 0;
    for (var i = 0; i < current_menu.length; i++) {
        sum += current_menu[i].price * current_menu[i].amount;
    }
    return sum;
}

function checkout() {
    var sum = 0;
    for (var i = 0; i < subtotal.length; i++) {
        sum += subtotal[i];
    }

    cashier.textContent = Math.round(sum * 100) / 100; // https://stackoverflow.com/a/11832950
}
