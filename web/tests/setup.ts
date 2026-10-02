// jsdom 没有实现 scrollTo；页面里只在换页、"重新查看"时调用，测试里当成空操作。
window.scrollTo = (() => {}) as typeof window.scrollTo;
Element.prototype.scrollIntoView = function scrollIntoView() {};
