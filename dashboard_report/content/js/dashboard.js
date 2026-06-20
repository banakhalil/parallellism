/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
var showControllersOnly = false;
var seriesFilter = "";
var filtersOnlySampleSeries = true;

/*
 * Add header in statistics table to group metrics by category
 * format
 *
 */
function summaryTableHeader(header) {
    var newRow = header.insertRow(-1);
    newRow.className = "tablesorter-no-sort";
    var cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Requests";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 3;
    cell.innerHTML = "Executions";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 7;
    cell.innerHTML = "Response Times (ms)";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Throughput";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 2;
    cell.innerHTML = "Network (KB/sec)";
    newRow.appendChild(cell);
}

/*
 * Populates the table identified by id parameter with the specified data and
 * format
 *
 */
function createTable(table, info, formatter, defaultSorts, seriesIndex, headerCreator) {
    var tableRef = table[0];

    // Create header and populate it with data.titles array
    var header = tableRef.createTHead();

    // Call callback is available
    if(headerCreator) {
        headerCreator(header);
    }

    var newRow = header.insertRow(-1);
    for (var index = 0; index < info.titles.length; index++) {
        var cell = document.createElement('th');
        cell.innerHTML = info.titles[index];
        newRow.appendChild(cell);
    }

    var tBody;

    // Create overall body if defined
    if(info.overall){
        tBody = document.createElement('tbody');
        tBody.className = "tablesorter-no-sort";
        tableRef.appendChild(tBody);
        var newRow = tBody.insertRow(-1);
        var data = info.overall.data;
        for(var index=0;index < data.length; index++){
            var cell = newRow.insertCell(-1);
            cell.innerHTML = formatter ? formatter(index, data[index]): data[index];
        }
    }

    // Create regular body
    tBody = document.createElement('tbody');
    tableRef.appendChild(tBody);

    var regexp;
    if(seriesFilter) {
        regexp = new RegExp(seriesFilter, 'i');
    }
    // Populate body with data.items array
    for(var index=0; index < info.items.length; index++){
        var item = info.items[index];
        if((!regexp || filtersOnlySampleSeries && !info.supportsControllersDiscrimination || regexp.test(item.data[seriesIndex]))
                &&
                (!showControllersOnly || !info.supportsControllersDiscrimination || item.isController)){
            if(item.data.length > 0) {
                var newRow = tBody.insertRow(-1);
                for(var col=0; col < item.data.length; col++){
                    var cell = newRow.insertCell(-1);
                    cell.innerHTML = formatter ? formatter(col, item.data[col]) : item.data[col];
                }
            }
        }
    }

    // Add support of columns sort
    table.tablesorter({sortList : defaultSorts});
}

$(document).ready(function() {

    // Customize table sorter default options
    $.extend( $.tablesorter.defaults, {
        theme: 'blue',
        cssInfoBlock: "tablesorter-no-sort",
        widthFixed: true,
        widgets: ['zebra']
    });

    var data = {"OkPercent": 100.0, "KoPercent": 0.0};
    var dataset = [
        {
            "label" : "FAIL",
            "data" : data.KoPercent,
            "color" : "#FF6347"
        },
        {
            "label" : "PASS",
            "data" : data.OkPercent,
            "color" : "#9ACD32"
        }];
    $.plot($("#flot-requests-summary"), dataset, {
        series : {
            pie : {
                show : true,
                radius : 1,
                label : {
                    show : true,
                    radius : 3 / 4,
                    formatter : function(label, series) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;">'
                            + label
                            + '<br/>'
                            + Math.round10(series.percent, -2)
                            + '%</div>';
                    },
                    background : {
                        opacity : 0.5,
                        color : '#000'
                    }
                }
            }
        },
        legend : {
            show : true
        }
    });

    // Creates APDEX table
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.5342857142857143, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [0.5, 500, 1500, "02. GET /api/me/"], "isController": false}, {"data": [0.625, 500, 1500, "09. DELETE /api/favorite/delete/"], "isController": false}, {"data": [0.5, 500, 1500, "06. POST /api/favorite/add/"], "isController": false}, {"data": [0.28, 500, 1500, "13. POST /api/orders/create/"], "isController": false}, {"data": [0.5, 500, 1500, "07. POST /api/cart/store/"], "isController": false}, {"data": [0.16, 500, 1500, "05. GET /api/products/{id}/"], "isController": false}, {"data": [0.33, 500, 1500, "03. POST /api/personal-info/"], "isController": false}, {"data": [1.0, 500, 1500, "10. GET /api/cart/"], "isController": false}, {"data": [0.78, 500, 1500, "12. GET /api/orders/user/"], "isController": false}, {"data": [0.0, 500, 1500, "01. POST /api/login/"], "isController": false}, {"data": [1.0, 500, 1500, "08. GET /api/favorite/"], "isController": false}, {"data": [1.0, 500, 1500, "11. POST /api/cart/increase/"], "isController": false}, {"data": [0.365, 500, 1500, "04. GET /api/products/"], "isController": false}, {"data": [0.44, 500, 1500, "14. POST /api/orders/{id}/pay/"], "isController": false}]}, function(index, item){
        switch(index){
            case 0:
                item = item.toFixed(3);
                break;
            case 1:
            case 2:
                item = formatDuration(item);
                break;
        }
        return item;
    }, [[0, 0]], 3);

    // Create statistics table
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 1400, 0, 0.0, 1038.1692857142857, 11, 3036, 860.0, 2538.0, 2975.0, 3027.0, 54.51501109769868, 49.16903395263035, 24.686599528834545], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["02. GET /api/me/", 100, 0, 0.0, 1053.8899999999999, 847, 1219, 1059.5, 1159.0, 1159.0, 1218.99, 79.05138339920948, 40.831892292490124, 33.81299407114625], "isController": false}, {"data": ["09. DELETE /api/favorite/delete/", 100, 0, 0.0, 654.0300000000001, 438, 813, 710.5, 765.0, 789.9, 812.81, 118.7648456057007, 46.97242428741093, 56.9468156175772], "isController": false}, {"data": ["06. POST /api/favorite/add/", 100, 0, 0.0, 922.1900000000003, 893, 1127, 909.0, 932.0, 1065.1499999999987, 1126.94, 88.1057268722467, 33.72797356828194, 41.815803964757706], "isController": false}, {"data": ["13. POST /api/orders/create/", 100, 0, 0.0, 1964.4000000000003, 820, 2980, 1318.0, 2976.0, 2979.0, 2980.0, 15.525539512498058, 7.338243285204161, 9.369905682347461], "isController": false}, {"data": ["07. POST /api/cart/store/", 100, 0, 0.0, 832.6799999999997, 759, 860, 853.5, 858.0, 859.95, 860.0, 116.14401858304298, 43.78085075493612, 57.278056039488966], "isController": false}, {"data": ["05. GET /api/products/{id}/", 100, 0, 0.0, 1462.4199999999998, 97, 1771, 1701.0, 1729.0, 1731.0, 1770.93, 51.36106831022085, 34.07285246533128, 22.420310092449924], "isController": false}, {"data": ["03. POST /api/personal-info/", 100, 0, 0.0, 1061.66, 321, 1824, 551.0, 1745.0, 1746.0, 1823.2899999999997, 39.5882818685669, 19.59774594220111, 19.868368962787017], "isController": false}, {"data": ["10. GET /api/cart/", 100, 0, 0.0, 95.73999999999998, 11, 140, 97.5, 133.0, 136.89999999999998, 139.99, 581.3953488372093, 447.9696584302326, 249.8183139534884], "isController": false}, {"data": ["12. GET /api/orders/user/", 100, 0, 0.0, 508.5899999999999, 71, 1051, 188.5, 1048.0, 1049.0, 1050.99, 51.38746145940391, 96.32690053314491, 22.43183132065776], "isController": false}, {"data": ["01. POST /api/login/", 100, 0, 0.0, 2348.810000000001, 1679, 2626, 2420.5, 2617.9, 2622.95, 2626.0, 38.051750380517504, 28.64731972983257, 9.587257420091325], "isController": false}, {"data": ["08. GET /api/favorite/", 100, 0, 0.0, 159.57000000000002, 114, 215, 146.0, 208.0, 210.0, 215.0, 294.11764705882354, 205.93979779411762, 127.52757352941175], "isController": false}, {"data": ["11. POST /api/cart/increase/", 100, 0, 0.0, 268.68, 159, 449, 246.5, 442.0, 447.95, 449.0, 89.04719501335707, 68.17675868210151, 42.34959372217275], "isController": false}, {"data": ["04. GET /api/products/", 100, 0, 0.0, 1382.4699999999996, 800, 2894, 1146.0, 2384.0, 2384.0, 2893.97, 22.060445621001545, 90.4512739907346, 9.565271343481138], "isController": false}, {"data": ["14. POST /api/orders/{id}/pay/", 100, 0, 0.0, 1819.2399999999998, 277, 3036, 3022.0, 3029.9, 3031.0, 3035.95, 19.474196689386563, 7.017557205452776, 8.995405306718599], "isController": false}]}, function(index, item){
        switch(index){
            // Errors pct
            case 3:
                item = item.toFixed(2) + '%';
                break;
            // Mean
            case 4:
            // Mean
            case 7:
            // Median
            case 8:
            // Percentile 1
            case 9:
            // Percentile 2
            case 10:
            // Percentile 3
            case 11:
            // Throughput
            case 12:
            // Kbytes/s
            case 13:
            // Sent Kbytes/s
                item = item.toFixed(2);
                break;
        }
        return item;
    }, [[0, 0]], 0, summaryTableHeader);

    // Create error table
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": []}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 1400, 0, "", "", "", "", "", "", "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}, {"data": [], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
