import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import { Manager as PopperManager, Reference as PopperReference, Popper } from 'react-popper'

const PopperModifiers = {
  preventOverflow: {
    boundariesElement: 'viewport'
  }
}

class SearchResultDescription extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired
  }

  render () {
    const { name, description } = this.props

    return ReactDOM.createPortal((
      <Popper modifiers={PopperModifiers} placement='right'>
        {({ ref, style, placement, arrowProps }) => (
          <div
            className={`module-search-result-description popover bs-popover-${placement}`}
            ref={ref}
            style={style}
            data-placement={placement}
          >
            <div className='arrow' {...arrowProps} />
            <h3>{name}</h3>
            <p>{description}</p>
          </div>
        )}
      </Popper>
    ), document.body)
  }
}

export default class SearchResult extends React.PureComponent {
  static propTypes = {
    isActive: PropTypes.bool.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    idName: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired, // func(idName) => undefined
    onMouseEnter: PropTypes.func.isRequired, // func(idName) => undefined
  }

  onClick = () => {
    this.props.onClick(this.props.idName)
  }

  onMouseEnter = () => {
    this.props.onMouseEnter(this.props.idName)
  }

  render() {
    const { idName, isActive, isLessonHighlight, isMatch, name, icon, description } = this.props

    const className = [ 'module-search-result' ]
    if (isLessonHighlight) className.push('lesson-highlight')

    // We need to use Popper here to position SearchResultDescription. We can't
    // just set it to position:absolute to the right of its menu item because
    // that would make the menu item wider than the menu -- which would add a
    // scrollbar to the menu.
    //
    // Nested Poppers! Whee!
    return (
      <PopperManager>
        <li>
          <PopperReference>
            {({ ref }) => (
              <button
                ref={ref}
                className={className.join(' ')}
                id={`module-search-result-${idName}`}
                data-module-slug={idName}
                data-module-name={name}
                onClick={this.onClick}
                onMouseEnter={this.onMouseEnter}
              >
                <i className={`icon-${icon}`} />
                <span className='name'>{name}</span>
              </button>
            )}
          </PopperReference>
          {isActive ? <SearchResultDescription name={name} description={description} /> : null}
        </li>
      </PopperManager>
    )
  }
}
