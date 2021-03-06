import React from 'react'
import PropTypes from 'prop-types'
import { withFetchedData } from './FetchedData'
import { FixedSizeList } from 'react-window'
import memoize from 'memoize-one'

const NumberFormatter = new Intl.NumberFormat()

// TODO: Change class names to move away from Refine and update CSS

/**
 * Displays a list item of check box, name (of item), and count
 */
class ValueItem extends React.PureComponent {
  static propTypes = {
    item: PropTypes.string, // new value -- may be empty string
    count: PropTypes.number.isRequired, // number, strictly greater than 0
    isSelected: PropTypes.bool.isRequired,
    onChangeItem: PropTypes.func.isRequired // func(item, isSelected) => undefined
  }

  onChangeItem = (ev) => {
    this.props.onChangeItem(this.props.item, ev.target.checked)
  }

  render () {
    const { count, item, isSelected } = this.props

    return (
      <label className='value'>
        <input
          name={`include[${item}]`}
          type='checkbox'
          title='Include these rows'
          checked={isSelected}
          onChange={this.onChangeItem}
        />
        <div className='text'>{item}</div>
        <div className='count'>{NumberFormatter.format(count)}</div>
      </label>
    )
  }
}

class ListRow extends React.PureComponent {
  // extend PureComponent so we get a shouldComponentUpdate() function

  // PropTypes all supplied by FixedSizeList
  static propTypes = {
    data: PropTypes.shape({
      valueCounts: PropTypes.object.isRequired, // { 'item': <Number> count, ... }
      items: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
      selection: PropTypes.instanceOf(Set).isRequired,
      onChangeItem: PropTypes.func.isRequired, // func(item, isSelected) => undefined
    }),
    style: PropTypes.object.isRequired,
    index: PropTypes.number.isRequired
  }

  render () {
    const { data: { valueCounts, items, selection, onChangeItem }, style, index } = this.props
    const item = items[index]
    const count = valueCounts[item]
    const isSelected = selection.has(item)

    return (
      <div style={style}>
        <ValueItem
          item={item}
          count={count}
          isSelected={isSelected}
          onChangeItem={onChangeItem}
        />
      </div>
    )
  }
}

export class AllNoneButtons extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    clearSelectedValues: PropTypes.func.isRequired, // func() => undefined
    fillSelectedValues: PropTypes.func.isRequired // func() => undefined
  }

  render() {
    const { isReadOnly, clearSelectedValues, fillSelectedValues } = this.props

    return (
      <div className="all-none-buttons">
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-all'
          title='Select All'
          onClick={fillSelectedValues}
          className='mc-select-all'
        >
          All
        </button>
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-none'
          title='Select None'
          onClick={clearSelectedValues}
          className='mc-select-none'
        >
          None
        </button>
      </div>
    )
  }
}

class ValueList extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // or null if loading or no column selected -- passed to <ListRow>
    loading: PropTypes.bool.isRequired,
    selection: PropTypes.instanceOf(Set).isRequired, // selected values -- passed to <ListRow>
    items: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // filtered search results -- passed to <ListRow>
    nItemsTotal: PropTypes.number.isRequired, // even when not searching
    itemHeight: PropTypes.number.isRequired, // height of a single value, in px
    maxHeight: PropTypes.number.isRequired, // max height of whole div
    onChangeItem: PropTypes.func.isRequired, // func(item, isSelected) => undefined -- passed to <ListRow>
  }

  _itemKey = (index, data) => data.items[index]

  innerRender () {
    const { valueCounts, loading, items, nItemsTotal, maxHeight, itemHeight } = this.props

    if (!valueCounts && !loading) {
      // Waiting for user to select a column
      return null
    } else if (loading) {
      return 'Loading values…'
    } else if (nItemsTotal === 0) {
      return 'Column does not have any values'
    } else if (items.length === 0) {
      return 'No values match your search'
    } else {
      const height = Math.min(maxHeight, items.length * itemHeight)
      return (
        <FixedSizeList
          className='react-list'
          height={height}
          itemSize={itemHeight}
          itemCount={items.length}
          itemData={this.props /* a bit more than we want, but not _much_ more than we want */}
          itemKey={this._itemKey}
        >
          {ListRow}
        </FixedSizeList>
      )
    }
  }

  render () {
    const { outerRef } = this.props

    return (
      <div className='value-list' ref={outerRef}>{this.innerRender()}</div>
    )
  }
}

/**
 * ValueList, with itemHeight and maxHeight calculated automatically.
 *
 * The trick is: first we render a dummy list and calculate those styles.
 * Then we delete the dummy list and use the calculated heights.
 */
class DynamicallySizedValueList extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.objectOf(PropTypes.number.isRequired), // value => count, or null if loading or no column selected -- passed to <ListRow>
    loading: PropTypes.bool.isRequired,
    selection: PropTypes.instanceOf(Set).isRequired, // selected values -- passed to <ListRow>
    items: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // filtered search results -- passed to <ListRow>
    nItemsTotal: PropTypes.number.isRequired, // even when not searching
    onChangeItem: PropTypes.func.isRequired, // func(item, isSelected) => undefined -- passed to <ListRow>
  }

  sizerRef = React.createRef()

  state = {
    itemHeight: null,
    maxHeight: null
  }

  componentDidMount () {
    const sizer = this.sizerRef.current

    const sizerStyle = window.getComputedStyle(sizer)
    let maxHeight
    if (!sizerStyle.maxHeight || sizerStyle.maxHeight === 'none') {
      maxHeight = Infinity
    } else {
      maxHeight = parseFloat(sizerStyle.maxHeight) // parseFloat: convert e.g. "300px" to 300
    }

    const item = sizer.querySelector('.value')
    window.x = item
    const itemHeight = item.clientHeight || 1

    this.setState({ maxHeight, itemHeight })
  }

  render () {
    const { itemHeight, maxHeight } = this.state

    if (itemHeight && maxHeight) {
      return (
        <ValueList
          itemHeight={itemHeight}
          maxHeight={maxHeight}
          {...this.props}
        />
      )
    } else {
      // This will only be rendered once, on initial render.
      // Draw a single-element list with a dummy height. That'll paint enough
      // to the DOM that we can calculate the _correct_ heights.
      return (
        <ValueList
          valueCounts={{'A': 1}}
          loading={false}
          selection={new Set()}
          items={['A']}
          nItemsTotal={1}
          itemHeight={1}
          maxHeight={1}
          onChangeItem={this.props.onChangeItem}
          outerRef={this.sizerRef}
        />
      )
    }
  }
}


const ItemCollator = new Intl.Collator() // in the user's locale

/**
 * The "value" here is an Array: `["value1", "value2"]`
 *
 * `valueCounts` describes the input: `{ "foo": 1, "bar": 3, ... }`
 */
export class ValueSelect extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null (when loading or waiting for user input) or { value1: n, value2: n, ... }
    loading: PropTypes.bool.isRequired,
    value: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // `["value1", "value2"]}`
    onChange: PropTypes.func.isRequired // fn(['value1', 'value2', 'value5'])
  }

  state = {
    searchInput: '', // <input type="search"> string input from the user
  }

  /**
   * Return a Set[String] derived from `value`.
   *
   * this.selection.has('A') => true|false
   */
  get selection () {
    return this._buildSelectedValues(this.props.value)
  }

  get sortedItems () {
    return this._buildSortedValues(this.props.valueCounts)
  }

  get matchingSortedItems () {
    return this._buildMatchingSortedItems(this.sortedItems, this.state.searchInput)
  }

  _buildSelectedValues = memoize(values => new Set(values))

  _buildSortedValues = memoize(valueCounts => {
    if (!valueCounts) return []
    return [ ...Object.keys(valueCounts).sort(ItemCollator.compare) ]
  })

  _buildMatchingSortedItems = memoize((sortedItems, searchInput) => {
    if (searchInput) {
      const searchKey = searchInput.toLowerCase()
      return sortedItems.filter(v => v.toLowerCase().includes(searchKey))
    } else {
      return sortedItems
    }
  })

  onResetSearch = () => {
    this.setState({ searchInput: '' })
  }

  onKeyDown = (ev) => {
    if (ev.keyCode === 27) this.onResetSearch() // Esc => reset
  }

  onInputChange = (ev) => {
    const searchInput = ev.target.value
    this.setState({ searchInput })
  }

  onChangeItem = (item, isSelected) => {
    const { value, onChange } = this.props
    if (isSelected) {
      if (!value.includes(item)) {
        onChange([ ...value, item ])
      } else {
        // no-op: adding an already-present element
      }
    } else {
      const index = value.indexOf(item)
      if (index !== -1) {
        onChange([
          ...(value.slice(0, index)),
          ...(value.slice(index + 1))
        ])
      } else {
        // no-op: deleting an already-missing element
      }
    }
  }

  clearSelectedValues = () => {
    this.props.onChange([])
  }

  fillSelectedValues = () => {
    const { onChange, valueCounts } = this.props
    if (!valueCounts) return // surely the user didn't mean to clear selection?
    onChange([ ...Object.keys(valueCounts) ])
  }

  render () {
    const { itemHeight, loading } = this.props
    const { searchInput } = this.state
    const canSearch = this.sortedItems.length > 1
    const isSearching = (searchInput !== '')

    return (
      <>
        { !canSearch ? null : (
          <>
            <div className="in-module--search" onSubmit={this.onSubmit} onReset={this.onReset}>
              <input
                type='search'
                placeholder='Search values...'
                autoComplete='off'
                value={searchInput}
                onChange={this.onInputChange}
                onKeyDown={this.onKeyDown}
              />
              <button
                type="button"
                onClick={this.onResetSearch}
                className="close"
                title="Clear Search"
              ><i className="icon-close" /></button>
            </div>
            <AllNoneButtons
              isReadOnly={isSearching}
              clearSelectedValues={this.clearSelectedValues}
              fillSelectedValues={this.fillSelectedValues}
            />
          </>
        )}
        <DynamicallySizedValueList
          valueCounts={this.props.valueCounts}
          loading={loading}
          selection={this.selection}
          nItemsTotal={this.sortedItems.length}
          items={this.matchingSortedItems}
          onChangeItem={this.onChangeItem}
        />
      </>
    )
  }
}

export default withFetchedData(
  ValueSelect,
  'valueCounts',
  ({ api, inputWfModuleId, selectedColumn }) => selectedColumn === null ? Promise.resolve(null) : api.valueCounts(inputWfModuleId, selectedColumn),
  ({ inputDeltaId, selectedColumn }) => selectedColumn === null ? null : `${inputDeltaId}-${selectedColumn}`
)
